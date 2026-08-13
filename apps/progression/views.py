from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.constants import Roles
from apps.core.permissions import HasRole
from apps.progression.models import ChapterUnlock, ChapterValidation, CourseProgressionSettings, CourseView, LessonProgress, XAPIStatement
from apps.progression.serializers import (
    ChapterStatusSerializer,
    ChapterValidationSerializer,
    CourseProgressionSettingsSerializer,
    CourseViewSerializer,
    LessonEventSerializer,
    LessonProgressSerializer,
    LessonProgressUpdateSerializer,
    XAPIStatementSerializer,
)
from apps.progression.services import (
    get_progression_settings,
    is_chapter_completed,
    is_chapter_unlocked,
    is_final_exam_unlocked,
    is_lesson_accessible,
    ordered_chapters,
    record_course_view,
    record_lesson_event,
    record_lesson_progress,
)

IsContentManager = HasRole.for_roles(Roles.TRAINER, Roles.COMPANY_ADMIN)
IsValidator = HasRole.for_roles(Roles.TRAINER, Roles.MANAGER, Roles.HR, Roles.COMPANY_ADMIN)


class CourseProgressionSettingsViewSet(viewsets.ModelViewSet):
    queryset = CourseProgressionSettings.objects.select_related('course').all()
    serializer_class = CourseProgressionSettingsSerializer
    permission_classes = [IsContentManager]
    filterset_fields = ['course']


class CourseProgressView(APIView):
    """Returns the lock/unlock status of every chapter in a course for the current learner —
    the data needed to render the §24.1 sequential progression UI, plus the course-level final
    exam's availability (learner must be at 100% lesson progress) and attempt history."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, course_id):
        from apps.assessments.models import Assessment, AssessmentAttempt
        from apps.courses.models import Course, Enrollment

        course = Course.objects.get(pk=course_id)
        chapters = ordered_chapters(course)

        rows = []
        for chapter in chapters:
            rows.append({
                'chapter_id': chapter.id,
                'title': chapter.title,
                'is_unlocked': is_chapter_unlocked(request.user, chapter),
                'is_completed': is_chapter_completed(request.user, chapter),
            })

        enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
        progress_percent = float(enrollment.progress_percent) if enrollment else 0

        final_exam_data = None
        final_exam = Assessment.objects.filter(course=course, chapter__isnull=True, is_published=True).first()
        if final_exam:
            settings = get_progression_settings(course)
            effective_max = final_exam.max_attempts
            if settings.max_attempts is not None:
                effective_max = min(effective_max, settings.max_attempts)

            attempts = list(
                AssessmentAttempt.objects.filter(assessment=final_exam, user=request.user).order_by('-attempt_number')
            )
            scores = [float(a.score) for a in attempts if a.score is not None]
            final_exam_data = {
                'id': final_exam.id,
                'title': final_exam.title,
                'passing_score': 100,
                'max_attempts': effective_max,
                'attempts_used': len(attempts),
                'attempts_remaining': max(0, effective_max - len(attempts)),
                'best_score': max(scores) if scores else None,
                'has_passed': any(score >= 100 for score in scores),
                'is_unlocked': progress_percent >= 100,
            }

        return Response({
            'chapters': ChapterStatusSerializer(rows, many=True).data,
            'final_exam_unlocked': is_final_exam_unlocked(request.user, course),
            'progress_percent': progress_percent,
            'final_exam': final_exam_data,
        })


class CourseProgressResetView(APIView):
    """Resets the current learner's progress for a course (all lesson completions, chapter
    unlocks/validations, and the enrollment's progress_percent/status) so they can retake it
    from scratch. Used by the "return to course" choice on the completion modal."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, course_id):
        from apps.courses.models import Course, Enrollment

        course = Course.objects.get(pk=course_id)
        try:
            enrollment = Enrollment.objects.get(user=request.user, course=course)
        except Enrollment.DoesNotExist:
            return Response({'detail': "Vous n'êtes pas inscrit à cette formation."}, status=404)

        LessonProgress.objects.filter(user=request.user, lesson__chapter__section__course=course).delete()
        ChapterUnlock.objects.filter(user=request.user, chapter__section__course=course).delete()
        ChapterValidation.objects.filter(user=request.user, chapter__section__course=course).delete()

        enrollment.progress_percent = 0
        enrollment.status = Enrollment.STATUS_IN_PROGRESS
        enrollment.completed_at = None
        enrollment.save(update_fields=['progress_percent', 'status', 'completed_at'])

        return Response({'detail': 'Progression réinitialisée.'})


class LessonAccessView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, lesson_id):
        from apps.courses.models import Lesson

        lesson = Lesson.objects.select_related('chapter').get(pk=lesson_id)
        accessible = is_lesson_accessible(request.user, lesson)
        return Response({'lesson_id': lesson.id, 'is_accessible': accessible})


class LessonProgressViewSet(viewsets.ModelViewSet):
    serializer_class = LessonProgressSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['lesson']
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        return LessonProgress.objects.filter(user=self.request.user).select_related('lesson')

    @action(detail=False, methods=['post'], url_path='update')
    def update_progress(self, request):
        from apps.courses.models import Lesson

        lesson_id = request.data.get('lesson_id')
        lesson = Lesson.objects.select_related('chapter').get(pk=lesson_id)

        if not is_lesson_accessible(request.user, lesson):
            return Response({'detail': 'Ce chapitre est verrouillé.'}, status=403)

        serializer = LessonProgressUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        scorm_completed = data.pop('mark_completed', None)
        progress = record_lesson_progress(request.user, lesson, scorm_completed=scorm_completed, **data)
        return Response(LessonProgressSerializer(progress).data)


class ChapterValidationViewSet(viewsets.ModelViewSet):
    queryset = ChapterValidation.objects.select_related('chapter', 'user', 'validated_by').all()
    serializer_class = ChapterValidationSerializer
    permission_classes = [IsValidator]
    filterset_fields = ['chapter', 'user']

    def perform_create(self, serializer):
        serializer.save(validated_by=self.request.user)


class LessonEventView(APIView):
    """POST /lessons/{id}/event/
    Enregistre un événement discret d'apprentissage (open, play, pause, document_view…).
    Appelé par le frontend/mobile à chaque interaction clé pour alimenter les KPI de tracking."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, lesson_id):
        from apps.courses.models import Lesson

        lesson = Lesson.objects.select_related('chapter__section__course').get(pk=lesson_id)
        serializer = LessonEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        record_lesson_event(
            user=request.user,
            lesson=lesson,
            verb=data['verb'],
            position_seconds=data.get('position_seconds'),
            time_spent_delta=data.get('time_spent_delta', 0),
        )
        return Response({'status': 'ok'}, status=201)


class LessonStatsView(APIView):
    """GET /lessons/{id}/stats/
    Statistiques détaillées d'une leçon : ouvertures, lectures vidéo, temps passé, complétion.
    Accessible aux admins, RH, managers et formateurs."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, lesson_id):
        from django.db.models import Avg, Count, Sum

        from apps.courses.models import Lesson

        lesson = Lesson.objects.select_related('chapter__section__course').get(pk=lesson_id)
        qs = LessonProgress.objects.filter(lesson=lesson)

        total_openers = qs.filter(open_count__gt=0).count()
        agg = qs.aggregate(
            total_opens=Sum('open_count'),
            total_plays=Sum('video_play_count'),
            avg_watch_percent=Avg('watch_percent'),
            avg_time_seconds=Avg('time_spent_seconds'),
            total_time_seconds=Sum('time_spent_seconds'),
            completions=Count('id', filter=__import__('django.db.models', fromlist=['Q']).Q(is_completed=True)),
        )
        total_learners = qs.count()

        return Response({
            'lesson_id': lesson_id,
            'lesson_title': lesson.title,
            'total_learners': total_learners,
            'total_openers': total_openers,
            'total_opens': agg['total_opens'] or 0,
            'total_video_plays': agg['total_plays'] or 0,
            'avg_watch_percent': round(float(agg['avg_watch_percent'] or 0), 2),
            'avg_time_spent_minutes': round((agg['avg_time_seconds'] or 0) / 60, 2),
            'total_time_spent_hours': round((agg['total_time_seconds'] or 0) / 3600, 2),
            'completion_count': agg['completions'] or 0,
            'completion_rate': round((agg['completions'] or 0) / total_learners * 100, 2) if total_learners else 0,
        })


class CourseViewLogView(APIView):
    """POST /courses/{id}/view/
    Incrémente le compteur d'ouvertures de la page cours pour l'utilisateur courant.
    Appelé par le frontend dès que la page de détail du cours est affichée."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, course_id):
        from apps.courses.models import Course

        course = Course.objects.get(pk=course_id)
        record_course_view(request.user, course)
        obj = CourseView.objects.get(user=request.user, course=course)
        return Response(CourseViewSerializer(obj).data, status=201)


class CourseStatsView(APIView):
    """GET /courses/{id}/stats/
    Statistiques complètes d'un cours : vues, leçons ouvertes, lectures vidéo, temps, progression.
    Accessible aux admins, RH, formateurs et managers."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, course_id):
        from django.db.models import Avg, Q, Sum

        from apps.courses.models import Course, Enrollment, Lesson

        course = Course.objects.get(pk=course_id)
        enrollments = Enrollment.objects.filter(course=course)
        lesson_ids = list(Lesson.objects.filter(chapter__section__course=course).values_list('id', flat=True))
        lp_qs = LessonProgress.objects.filter(lesson_id__in=lesson_ids)
        view_qs = CourseView.objects.filter(course=course)

        enroll_count = enrollments.count()
        completed_count = enrollments.filter(status=Enrollment.STATUS_COMPLETED).count()
        lp_agg = lp_qs.aggregate(
            total_opens=Sum('open_count'),
            total_plays=Sum('video_play_count'),
            total_time_s=Sum('time_spent_seconds'),
            avg_time_s=Avg('time_spent_seconds'),
        )
        views_agg = view_qs.aggregate(total_opens=Sum('open_count'))

        # Par leçon : top 5 les plus vues
        from django.db.models import Sum as S
        top_lessons = (
            lp_qs.values('lesson__id', 'lesson__title')
            .annotate(plays=S('video_play_count'), opens=S('open_count'), time_s=S('time_spent_seconds'))
            .order_by('-plays')[:5]
        )

        # Progression moyenne par leçon
        lesson_progress = (
            lp_qs.values('lesson__id', 'lesson__title')
            .annotate(avg_watch=Avg('watch_percent'), completions=__import__('django.db.models', fromlist=['Count']).Count('id', filter=Q(is_completed=True)))
            .order_by('lesson__id')
        )

        return Response({
            'course_id': course_id,
            'course_title': course.title,
            'total_enrolled': enroll_count,
            'completion_count': completed_count,
            'completion_rate': round(completed_count / enroll_count * 100, 2) if enroll_count else 0,
            'avg_progress_percent': round(float(enrollments.aggregate(avg=Avg('progress_percent'))['avg'] or 0), 2),
            'total_course_page_opens': views_agg['total_opens'] or 0,
            'unique_visitors': view_qs.count(),
            'total_lesson_opens': lp_agg['total_opens'] or 0,
            'total_video_plays': lp_agg['total_plays'] or 0,
            'total_time_spent_hours': round((lp_agg['total_time_s'] or 0) / 3600, 2),
            'avg_time_per_learner_minutes': round((lp_agg['avg_time_s'] or 0) / 60, 2),
            'top_lessons_by_plays': list(top_lessons),
            'lesson_progress': list(lesson_progress),
        })


class XAPIStatementViewSet(viewsets.ModelViewSet):
    serializer_class = XAPIStatementSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']
    filterset_fields = ['verb', 'object_type']

    def get_queryset(self):
        user = self.request.user
        qs = XAPIStatement.objects.all()
        if user.is_superuser or user.role in (Roles.SUPER_ADMIN, Roles.HR, Roles.COMPANY_ADMIN):
            return qs
        return qs.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, raw_statement=self.request.data)
