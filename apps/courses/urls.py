from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.courses.views import (
    ChapterViewSet,
    CourseSectionViewSet,
    CourseViewSet,
    EnrollmentViewSet,
    LessonAnswerViewSet,
    LessonPlayerView,
    LessonQuestionViewSet,
    LessonReviewViewSet,
    LessonViewSet,
    ReviewViewSet,
    ScormRegistrationView,
    TrainingRequestViewSet,
)

router = DefaultRouter()
router.register('courses', CourseViewSet, basename='course')
router.register('sections', CourseSectionViewSet, basename='course-section')
router.register('chapters', ChapterViewSet, basename='chapter')
router.register('lessons', LessonViewSet, basename='lesson')
router.register('lesson-questions', LessonQuestionViewSet, basename='lesson-question')
router.register('lesson-answers', LessonAnswerViewSet, basename='lesson-answer')
router.register('reviews', ReviewViewSet, basename='review')
router.register('lesson-reviews', LessonReviewViewSet, basename='lesson-review')
router.register('enrollments', EnrollmentViewSet, basename='enrollment')
router.register('training-requests', TrainingRequestViewSet, basename='training-request')

urlpatterns = [
    path('lessons/<int:lesson_id>/scorm-registration/', ScormRegistrationView.as_view(), name='scorm-registration'),
    path('lessons/<int:lesson_id>/player/', LessonPlayerView.as_view(), name='lesson-player'),
] + router.urls
