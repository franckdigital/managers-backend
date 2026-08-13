from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.assessments.models import Assessment, AssessmentAttempt, AssessmentQuestion, AssignmentSubmission, AttemptAnswer, Question, QuestionBank, QuestionChoice
from apps.assessments.serializers import (
    AssessmentAttemptSerializer,
    AssessmentQuestionSerializer,
    AssessmentSerializer,
    AssignmentSubmissionSerializer,
    AttemptAnswerSubmitSerializer,
    GradeAssignmentSerializer,
    ProctoringEventSerializer,
    QuestionBankSerializer,
    QuestionPublicSerializer,
    QuestionSerializer,
)
from apps.assessments.services import grade_attempt, is_attempt_expired, record_proctoring_event, start_attempt
from apps.core.constants import Roles
from apps.core.permissions import HasRole

IsContentManager = HasRole.for_roles(Roles.TRAINER, Roles.COMPANY_ADMIN, Roles.TRAINING_CENTER_ADMIN)


class QuestionBankViewSet(viewsets.ModelViewSet):
    queryset = QuestionBank.objects.prefetch_related('questions__choices').all()
    serializer_class = QuestionBankSerializer
    permission_classes = [IsContentManager]
    filterset_fields = ['company']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, company=self.request.user.company)


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.prefetch_related('choices').all()
    serializer_class = QuestionSerializer
    permission_classes = [IsContentManager]
    filterset_fields = ['bank', 'question_type', 'difficulty']

    def perform_create(self, serializer):
        question = serializer.save()
        choices_data = question.metadata.get('choices', [])
        if choices_data:
            QuestionChoice.objects.bulk_create([
                QuestionChoice(
                    question=question,
                    text=c.get('text', ''),
                    is_correct=c.get('is_correct', False),
                    order=i,
                )
                for i, c in enumerate(choices_data)
                if c.get('text', '').strip()
            ])
            question.metadata = {}
            question.save(update_fields=['metadata'])


class AssessmentViewSet(viewsets.ModelViewSet):
    queryset = Assessment.objects.select_related('course', 'chapter', 'question_bank').prefetch_related('assessment_questions').all()
    serializer_class = AssessmentSerializer
    filterset_fields = ['course', 'chapter', 'assessment_type']

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'start'):
            return [permissions.IsAuthenticated()]
        return [IsContentManager()]

    def perform_create(self, serializer):
        assessment = serializer.save()
        if assessment.question_bank_id and not assessment.is_randomized:
            questions = list(assessment.question_bank.questions.order_by('created_at'))
            AssessmentQuestion.objects.bulk_create([
                AssessmentQuestion(assessment=assessment, question=q, order=i)
                for i, q in enumerate(questions)
            ], ignore_conflicts=True)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        assessment = self.get_object()
        try:
            attempt = start_attempt(assessment, request.user)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=400)

        questions = Question.objects.filter(id__in=attempt.questions_snapshot).prefetch_related('choices')
        return Response({
            'attempt': AssessmentAttemptSerializer(attempt).data,
            'questions': QuestionPublicSerializer(questions, many=True).data,
        })


class AssessmentAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AssessmentAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['assessment', 'status']

    def get_queryset(self):
        user = self.request.user
        qs = AssessmentAttempt.objects.select_related('assessment', 'user').prefetch_related('answers')
        if user.is_superuser or user.role in (Roles.SUPER_ADMIN, Roles.TRAINER, Roles.COMPANY_ADMIN, Roles.HR):
            return qs
        return qs.filter(user=user)

    @action(detail=True, methods=['post'])
    def answer(self, request, pk=None):
        attempt = self.get_object()
        if attempt.user != request.user:
            return Response({'detail': 'Non autorisé.'}, status=403)
        if attempt.status != AssessmentAttempt.STATUS_IN_PROGRESS:
            return Response({'detail': 'Tentative déjà soumise.'}, status=400)
        if is_attempt_expired(attempt):
            grade_attempt(attempt, timed_out=True)
            return Response({'detail': 'Temps écoulé — la tentative a été soumise automatiquement.'}, status=403)

        serializer = AttemptAnswerSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        question = Question.objects.get(pk=data['question_id'])

        answer, _ = AttemptAnswer.objects.update_or_create(
            attempt=attempt, question=question,
            defaults={'text_answer': data['text_answer'], 'matching_answer': data['matching_answer']},
        )
        if data['selected_choice_ids']:
            answer.selected_choices.set(data['selected_choice_ids'])
        return Response({'detail': 'Réponse enregistrée.'})

    @action(detail=True, methods=['post'])
    def finish(self, request, pk=None):
        attempt = self.get_object()
        if attempt.user != request.user:
            return Response({'detail': 'Non autorisé.'}, status=403)
        graded = grade_attempt(attempt, timed_out=is_attempt_expired(attempt))
        return Response(AssessmentAttemptSerializer(graded).data)

    @action(detail=True, methods=['post'], url_path='report-event')
    def report_event(self, request, pk=None):
        """§7 — examen anti-fraude: le frontend remonte ici les signaux suspects détectés
        pendant la tentative (changement d'onglet, sortie plein écran, etc.)."""

        attempt = self.get_object()
        if attempt.user != request.user:
            return Response({'detail': 'Non autorisé.'}, status=403)
        if not attempt.assessment.anti_cheat_enabled:
            return Response({'detail': "L'anti-fraude n'est pas activé pour cette évaluation."}, status=400)

        serializer = ProctoringEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record_proctoring_event(attempt, serializer.validated_data['event_type'], serializer.validated_data['details'])
        return Response({'detail': 'Événement enregistré.'})

    @action(detail=True, methods=['post'], url_path='submit-assignment')
    def submit_assignment(self, request, pk=None):
        attempt = self.get_object()
        if is_attempt_expired(attempt):
            return Response({'detail': 'Le délai de soumission est dépassé.'}, status=403)

        serializer = AssignmentSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submission, _ = AssignmentSubmission.objects.update_or_create(
            attempt=attempt, defaults=serializer.validated_data
        )
        attempt.status = AssessmentAttempt.STATUS_SUBMITTED
        attempt.save(update_fields=['status'])
        return Response(AssignmentSubmissionSerializer(submission).data)


class AssessmentQuestionViewSet(viewsets.ModelViewSet):
    serializer_class = AssessmentQuestionSerializer
    permission_classes = [IsContentManager]
    filterset_fields = ['assessment']

    def get_queryset(self):
        return AssessmentQuestion.objects.select_related(
            'question'
        ).order_by('order').all()


class AssignmentSubmissionViewSet(viewsets.ModelViewSet):
    queryset = AssignmentSubmission.objects.select_related('attempt__user', 'attempt__assessment').all()
    serializer_class = AssignmentSubmissionSerializer
    permission_classes = [IsContentManager]
    http_method_names = ['get', 'post', 'head', 'options']

    @action(detail=True, methods=['post'])
    def grade(self, request, pk=None):
        submission = self.get_object()
        serializer = GradeAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        submission.grade = serializer.validated_data['grade']
        submission.feedback = serializer.validated_data.get('feedback', '')
        submission.graded_by = request.user
        from django.utils import timezone
        submission.graded_at = timezone.now()
        submission.save()

        attempt = submission.attempt
        attempt.score = submission.grade
        attempt.is_passed = submission.grade >= attempt.assessment.passing_score
        attempt.status = AssessmentAttempt.STATUS_GRADED
        attempt.save(update_fields=['score', 'is_passed', 'status'])

        if attempt.is_passed:
            from apps.gamification.services import award_quiz_pass_xp

            award_quiz_pass_xp(attempt.user, attempt.assessment)

        from apps.progression.services import record_xapi_statement

        record_xapi_statement(
            attempt.user, 'passed' if attempt.is_passed else 'failed', 'assessment', attempt.assessment_id,
            object_name=attempt.assessment.title, result={'success': attempt.is_passed, 'score': {'raw': float(submission.grade)}},
        )

        from apps.notifications.services import notify_user

        notify_user(
            attempt.user,
            'Devoir noté',
            f"Votre devoir pour « {attempt.assessment.title} » a été noté : {submission.grade}.",
            data={'submission_id': submission.id},
        )

        return Response(AssignmentSubmissionSerializer(submission).data)
