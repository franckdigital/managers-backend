from rest_framework.routers import DefaultRouter

from apps.learning_paths.views import (
    LearningPathEnrollmentViewSet,
    LearningPathStepViewSet,
    LearningPathViewSet,
    TrainingSessionViewSet,
)

router = DefaultRouter()
router.register('learning-paths', LearningPathViewSet, basename='learning-path')
router.register('learning-path-steps', LearningPathStepViewSet, basename='learning-path-step')
router.register('learning-path-enrollments', LearningPathEnrollmentViewSet, basename='learning-path-enrollment')
router.register('sessions', TrainingSessionViewSet, basename='training-session')

urlpatterns = router.urls
