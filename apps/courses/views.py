from django.conf import settings
from django.db.models import Q
from django.http import Http404
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.constants import Roles
from apps.core.mixins import AuditLogMixin
from apps.core.permissions import HasPermCode, HasRole
from apps.courses.models import (
    Chapter,
    Course,
    CourseSection,
    Enrollment,
    Lesson,
    LessonAnswer,
    LessonQuestion,
    LessonReview,
    Review,
    ScormRegistration,
    TrainingRequest,
)
from apps.courses.serializers import (
    AssignCourseSerializer,
    ChapterSerializer,
    CourseDetailSerializer,
    CourseListSerializer,
    CourseSectionSerializer,
    EnrollmentSerializer,
    LessonAnswerSerializer,
    LessonPlayerSerializer,
    LessonQuestionSerializer,
    LessonReviewSerializer,
    LessonSerializer,
    ReviewSerializer,
    ScormCommitSerializer,
    ScormRegistrationSerializer,
    TrainingRequestSerializer,
)
from apps.courses.services import assign_course, commit_scorm_cmi, recompute_course_rating

IsContentManager = HasRole.for_roles(Roles.TRAINER, Roles.COMPANY_ADMIN, Roles.TRAINING_CENTER_ADMIN)


class CourseViewSet(AuditLogMixin, viewsets.ModelViewSet):
    queryset = Course.objects.select_related('category', 'instructor', 'company').all()
    filterset_fields = ['category', 'level', 'status', 'is_free', 'company']
    search_fields = ['title', 'subtitle', 'description']

    def get_serializer_class(self):
        if self.action in ('list',):
            return CourseListSerializer
        return CourseDetailSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [permissions.AllowAny()]
        return [IsContentManager()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        # Super admin / superuser sees everything
        if user.is_authenticated and (user.is_superuser or user.role == Roles.SUPER_ADMIN):
            return qs

        if self.action in ('update', 'partial_update', 'destroy'):
            if user.role == Roles.TRAINER:
                return qs.filter(instructor=user)
            return qs.filter(company_id=user.company_id)

        if self.action == 'create':
            return qs

        if user.is_authenticated:
            own = Q(instructor=user)
            if user.company_id:
                own |= Q(company_id=user.company_id)
            qs = qs.filter(Q(status=Course.STATUS_PUBLISHED) | own)
            if user.company_id:
                # Company employees see their company's courses + the public B2C catalog
                visible_company = Q(company_id=user.company_id) | Q(company__isnull=True, is_company_internal=False)
            else:
                visible_company = Q(company__isnull=True, is_company_internal=False)
        else:
            qs = qs.filter(status=Course.STATUS_PUBLISHED)
            visible_company = Q(company__isnull=True, is_company_internal=False)

        return qs.filter(visible_company).distinct()

    def perform_create(self, serializer):
        user = self.request.user
        kwargs = {}
        if user.role == Roles.TRAINER:
            kwargs['instructor'] = user
        if not serializer.validated_data.get('company') and user.company_id:
            kwargs['company'] = user.company
        serializer.save(**kwargs)

    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        course = self.get_object()
        return Response(ReviewSerializer(course.reviews.select_related('user'), many=True).data)


class CourseSectionViewSet(viewsets.ModelViewSet):
    queryset = CourseSection.objects.select_related('course').all()
    serializer_class = CourseSectionSerializer
    filterset_fields = ['course']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [permissions.IsAuthenticated()]
        return [IsContentManager()]


class ChapterViewSet(viewsets.ModelViewSet):
    queryset = Chapter.objects.select_related('section').all()
    serializer_class = ChapterSerializer
    filterset_fields = ['section']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [permissions.IsAuthenticated()]
        return [IsContentManager()]


class LessonViewSet(viewsets.ModelViewSet):
    """Content authoring only. Students must use the content_security secured-streaming
    endpoints to access actual media — this viewset is gated to trainers/admins."""

    queryset = Lesson.objects.select_related('chapter').all()
    serializer_class = LessonSerializer
    permission_classes = [IsContentManager]
    filterset_fields = ['chapter', 'content_type']

    @action(detail=False, methods=['post'], url_path='presign-upload')
    def presign_upload(self, request):
        """Step 1 of a direct browser->R2 upload (bypasses nginx/Cloudflare body-size
        limits entirely for large course videos): hand back a short-lived signed PUT
        URL, never touching the file's bytes ourselves."""
        from apps.core.storage import generate_presigned_upload, max_direct_upload_bytes

        if not settings.USE_R2_STORAGE:
            return Response({'detail': "L'upload direct n'est pas configuré (R2 désactivé)."}, status=400)

        filename = request.data.get('filename') or ''
        content_type = request.data.get('content_type') or 'application/octet-stream'
        kind = request.data.get('kind') or 'document'
        try:
            size = int(request.data.get('size') or 0)
        except (TypeError, ValueError):
            size = 0

        if not filename:
            return Response({'detail': 'filename requis.'}, status=400)
        max_bytes = max_direct_upload_bytes()
        if size > max_bytes:
            return Response({'detail': f'Fichier trop volumineux (max {max_bytes // (1024 * 1024)} Mo).'}, status=400)

        folder = 'courses/videos' if kind == 'video' else 'courses/documents'
        return Response(generate_presigned_upload(filename=filename, content_type=content_type, folder=folder))

    @action(detail=True, methods=['post'], url_path='scorm-import')
    def scorm_import(self, request, pk=None):
        from apps.courses.scorm import import_scorm_package

        lesson = self.get_object()
        try:
            import_scorm_package(lesson)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=400)
        return Response(LessonSerializer(lesson).data)

    @action(detail=True, methods=['post'], url_path='generate-transcript')
    def generate_transcript(self, request, pk=None):
        """§Sous-titrage automatique — transcrit la vidéo/audio de la leçon via le
        fournisseur IA configuré (whisper pour OpenAI ; placeholder explicite sinon)."""
        from apps.ai_engine.providers import get_ai_provider

        lesson = self.get_object()
        if lesson.content_type not in (Lesson.TYPE_VIDEO, Lesson.TYPE_AUDIO) or not lesson.video_file:
            return Response({'detail': 'Cette leçon ne contient pas de média audio/vidéo à transcrire.'}, status=400)

        try:
            with lesson.video_file.open('rb') as file_obj:
                transcript = get_ai_provider().transcribe(file_obj)
        except NotImplementedError:
            return Response({'detail': "Le fournisseur IA actif ne prend pas en charge la transcription."}, status=400)
        except Exception as exc:
            return Response({'detail': str(exc)}, status=400)

        lesson.transcript = transcript
        lesson.save(update_fields=['transcript'])
        return Response(LessonSerializer(lesson).data)


class LessonPlayerView(APIView):
    """Learner-facing lesson detail (§24/§25): returns the safe fields only — raw media
    URLs never leave the server, the player must request a signed ticket from
    content_security for the actual video/document/SCORM bytes."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, lesson_id):
        from apps.progression.services import is_lesson_accessible

        try:
            lesson = Lesson.objects.select_related('chapter__section__course').get(pk=lesson_id)
        except Lesson.DoesNotExist:
            raise Http404

        course = lesson.course
        if not _can_access_course_qa(request.user, course):
            return Response({'detail': "Vous n'êtes pas inscrit à cette formation."}, status=403)

        if not is_lesson_accessible(request.user, lesson):
            return Response({'detail': 'Ce chapitre est verrouillé (progression séquentielle).'}, status=403)

        return Response(LessonPlayerSerializer(lesson).data)


def _can_access_course_qa(user, course):
    if user.is_superuser or user.role == Roles.SUPER_ADMIN:
        return True
    if course.instructor_id == user.id:
        return True
    if user.role in (Roles.COMPANY_ADMIN, Roles.HR) and course.company_id and course.company_id == user.company_id:
        return True
    from apps.tenants.services import has_active_b2c_subscription, has_active_team_subscription
    if has_active_team_subscription(user) or has_active_b2c_subscription(user):
        return True
    return Enrollment.objects.filter(user=user, course=course).exists()


class LessonQuestionViewSet(viewsets.ModelViewSet):
    queryset = LessonQuestion.objects.select_related('lesson', 'author').prefetch_related('answers')
    serializer_class = LessonQuestionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['lesson']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or user.role == Roles.SUPER_ADMIN:
            return qs
        return qs.filter(
            Q(lesson__chapter__section__course__instructor=user)
            | Q(lesson__chapter__section__course__enrollments__user=user)
            | Q(lesson__chapter__section__course__company_id=user.company_id, author__role__in=(Roles.COMPANY_ADMIN, Roles.HR))
        ).distinct()

    def perform_create(self, serializer):
        lesson = serializer.validated_data['lesson']
        if not _can_access_course_qa(self.request.user, lesson.course):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Vous devez être inscrit à ce cours pour poser une question.")
        serializer.save(author=self.request.user)


class LessonAnswerViewSet(viewsets.ModelViewSet):
    queryset = LessonAnswer.objects.select_related('question', 'author')
    serializer_class = LessonAnswerSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['question']

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or user.role == Roles.SUPER_ADMIN:
            return qs
        return qs.filter(
            Q(question__lesson__chapter__section__course__instructor=user)
            | Q(question__lesson__chapter__section__course__enrollments__user=user)
        ).distinct()

    def perform_create(self, serializer):
        question = serializer.validated_data['question']
        course = question.lesson.course
        user = self.request.user
        if not _can_access_course_qa(user, course):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Vous devez être inscrit à ce cours pour répondre.")
        serializer.save(author=user, is_instructor_answer=course.instructor_id == user.id)


class ScormRegistrationView(APIView):
    """The real SCORM RTE contract: the package's JS API wrapper (LMSGetValue/SetValue/
    Commit for 1.2, GetValue/SetValue/Commit for 2004 — implemented client-side inside the
    SCORM player iframe) calls GET to resume and POST to commit cmi.* values here."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, lesson_id):
        from apps.progression.services import is_lesson_accessible

        try:
            lesson = Lesson.objects.select_related('chapter').get(pk=lesson_id)
        except Lesson.DoesNotExist:
            raise Http404

        if not is_lesson_accessible(request.user, lesson):
            return Response({'detail': 'Ce chapitre est verrouillé.'}, status=403)

        registration, _ = ScormRegistration.objects.get_or_create(user=request.user, lesson=lesson)
        return Response(ScormRegistrationSerializer(registration).data)

    def post(self, request, lesson_id):
        from apps.progression.services import is_lesson_accessible

        try:
            lesson = Lesson.objects.select_related('chapter').get(pk=lesson_id)
        except Lesson.DoesNotExist:
            raise Http404

        if not is_lesson_accessible(request.user, lesson):
            return Response({'detail': 'Ce chapitre est verrouillé.'}, status=403)

        serializer = ScormCommitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        registration = commit_scorm_cmi(request.user, lesson, serializer.validated_data['cmi'])
        return Response(ScormRegistrationSerializer(registration).data)


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.select_related('user', 'course').all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['course']

    def perform_create(self, serializer):
        review = serializer.save(user=self.request.user)
        recompute_course_rating(review.course)

    def perform_update(self, serializer):
        review = serializer.save()
        recompute_course_rating(review.course)


class LessonReviewViewSet(viewsets.ModelViewSet):
    queryset = LessonReview.objects.select_related('user', 'lesson').all()
    serializer_class = LessonReviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['lesson', 'user']

    def perform_create(self, serializer):
        # (user, lesson) is unique — a stale "does a review already exist?" check on the
        # client (e.g. that GET failing/racing) can otherwise send a second create and
        # crash with an unhandled IntegrityError (500) instead of just updating it.
        lesson = serializer.validated_data.get('lesson')
        existing = LessonReview.objects.filter(user=self.request.user, lesson=lesson).first()
        if existing:
            serializer.instance = existing
        serializer.save(user=self.request.user)


class EnrollmentViewSet(viewsets.ModelViewSet):
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['course', 'status', 'source']
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        qs = Enrollment.objects.select_related('course', 'user')
        if user.is_superuser or user.role == Roles.SUPER_ADMIN:
            return qs
        if user.role in (Roles.COMPANY_ADMIN, Roles.HR):
            return qs.filter(user__company_id=user.company_id)
        if user.role == Roles.MANAGER:
            return qs.filter(user__manager=user)
        return qs.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, source=Enrollment.SOURCE_FREE)

    @action(detail=False, methods=['post'], permission_classes=[HasRole.for_roles(Roles.MANAGER, Roles.HR, Roles.COMPANY_ADMIN)])
    def assign(self, request):
        from apps.accounts.models import User

        serializer = AssignCourseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_user = User.objects.get(pk=serializer.validated_data['user_id'])
        course = Course.objects.get(pk=serializer.validated_data['course_id'])
        enrollment = assign_course(
            target_user, course, assigned_by=request.user, due_date=serializer.validated_data.get('due_date')
        )
        return Response(EnrollmentSerializer(enrollment).data)

    @action(detail=False, methods=['get'], url_path='my-learning')
    def my_learning(self, request):
        qs = Enrollment.objects.filter(user=request.user).select_related('course')
        return Response(EnrollmentSerializer(qs, many=True).data)


class TrainingRequestViewSet(viewsets.ModelViewSet):
    """Training requests submitted by managers/employees; reviewed by HR or company admin."""

    serializer_class = TrainingRequestSerializer
    permission_classes = [HasPermCode.for_code('training_request.view')]
    filterset_fields = ['status', 'urgency', 'requested_by', 'for_user']

    def get_queryset(self):
        user = self.request.user
        qs = TrainingRequest.objects.select_related('requested_by', 'for_user', 'course', 'reviewed_by')
        if user.is_superuser or user.role in (Roles.SUPER_ADMIN, Roles.COMPANY_ADMIN, Roles.HR):
            return qs.filter(requested_by__company_id=user.company_id) if user.company_id else qs
        if user.role == Roles.MANAGER:
            return qs.filter(Q(requested_by=user) | Q(for_user__manager=user))
        return qs.filter(Q(requested_by=user) | Q(for_user=user))

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        from django.utils import timezone
        if request.user.role not in (Roles.SUPER_ADMIN, Roles.COMPANY_ADMIN, Roles.HR):
            return Response({'detail': 'Accès refusé.'}, status=403)
        req = self.get_object()
        req.status = TrainingRequest.STATUS_APPROVED
        req.reviewed_by = request.user
        req.review_notes = request.data.get('notes', '')
        req.reviewed_at = timezone.now()
        req.save(update_fields=['status', 'reviewed_by', 'review_notes', 'reviewed_at'])
        return Response(TrainingRequestSerializer(req).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        from django.utils import timezone
        if request.user.role not in (Roles.SUPER_ADMIN, Roles.COMPANY_ADMIN, Roles.HR):
            return Response({'detail': 'Accès refusé.'}, status=403)
        req = self.get_object()
        req.status = TrainingRequest.STATUS_REJECTED
        req.reviewed_by = request.user
        req.review_notes = request.data.get('notes', '')
        req.reviewed_at = timezone.now()
        req.save(update_fields=['status', 'reviewed_by', 'review_notes', 'reviewed_at'])
        return Response(TrainingRequestSerializer(req).data)
