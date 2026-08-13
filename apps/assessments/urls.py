from rest_framework.routers import DefaultRouter

from apps.assessments.views import (
    AssessmentAttemptViewSet,
    AssessmentQuestionViewSet,
    AssessmentViewSet,
    AssignmentSubmissionViewSet,
    QuestionBankViewSet,
    QuestionViewSet,
)

router = DefaultRouter()
router.register('question-banks', QuestionBankViewSet, basename='question-bank')
router.register('questions', QuestionViewSet, basename='question')
router.register('assessments', AssessmentViewSet, basename='assessment')
router.register('assessment-questions', AssessmentQuestionViewSet, basename='assessment-question')
router.register('attempts', AssessmentAttemptViewSet, basename='assessment-attempt')
router.register('assignment-submissions', AssignmentSubmissionViewSet, basename='assignment-submission')

urlpatterns = router.urls
