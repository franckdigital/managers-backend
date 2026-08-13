from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.progression.views import (
    ChapterValidationViewSet,
    CourseProgressionSettingsViewSet,
    CourseProgressResetView,
    CourseProgressView,
    CourseStatsView,
    CourseViewLogView,
    LessonAccessView,
    LessonEventView,
    LessonProgressViewSet,
    LessonStatsView,
    XAPIStatementViewSet,
)

router = DefaultRouter()
router.register('progression-settings', CourseProgressionSettingsViewSet, basename='progression-settings')
router.register('lesson-progress', LessonProgressViewSet, basename='lesson-progress')
router.register('chapter-validations', ChapterValidationViewSet, basename='chapter-validation')
router.register('xapi-statements', XAPIStatementViewSet, basename='xapi-statement')

urlpatterns = [
    # Progression de cours
    path('courses/<int:course_id>/progress/', CourseProgressView.as_view(), name='course-progress'),
    path('courses/<int:course_id>/progress/reset/', CourseProgressResetView.as_view(), name='course-progress-reset'),
    # Tracking vues & stats cours
    path('courses/<int:course_id>/view/', CourseViewLogView.as_view(), name='course-view'),
    path('courses/<int:course_id>/stats/', CourseStatsView.as_view(), name='course-stats'),
    # Tracking événements & stats leçon
    path('lessons/<int:lesson_id>/access/', LessonAccessView.as_view(), name='lesson-access'),
    path('lessons/<int:lesson_id>/event/', LessonEventView.as_view(), name='lesson-event'),
    path('lessons/<int:lesson_id>/stats/', LessonStatsView.as_view(), name='lesson-stats'),
] + router.urls
