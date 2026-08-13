from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.content_security.views import (
    MyAccessLogView,
    PackageLessonHLSView,
    ReportSuspiciousActivityView,
    SecureHLSKeyView,
    SecureHLSManifestView,
    SecureHLSSegmentView,
    SecureMediaFileView,
    SecureResourceFileView,
    SecureResourceTicketView,
    SecureStreamTicketView,
    SuspiciousActivityEventViewSet,
)

router = DefaultRouter()
router.register('suspicious-activity', SuspiciousActivityEventViewSet, basename='suspicious-activity')

urlpatterns = [
    path('lessons/<int:lesson_id>/ticket/', SecureStreamTicketView.as_view(), name='secure-stream-ticket'),
    path('lessons/<int:lesson_id>/file/', SecureMediaFileView.as_view(), name='secure-media-file'),
    path('lessons/<int:lesson_id>/package-hls/', PackageLessonHLSView.as_view(), name='package-lesson-hls'),
    path('lessons/<int:lesson_id>/hls/manifest.m3u8', SecureHLSManifestView.as_view(), name='secure-hls-manifest'),
    path('lessons/<int:lesson_id>/hls/key/', SecureHLSKeyView.as_view(), name='secure-hls-key'),
    path('lessons/<int:lesson_id>/hls/<str:segment_name>', SecureHLSSegmentView.as_view(), name='secure-hls-segment'),
    path('resources/<int:resource_id>/ticket/', SecureResourceTicketView.as_view(), name='secure-resource-ticket'),
    path('resources/<int:resource_id>/file/', SecureResourceFileView.as_view(), name='secure-resource-file'),
    path('my-access-logs/', MyAccessLogView.as_view(), name='my-access-logs'),
    path('report-suspicious-activity/', ReportSuspiciousActivityView.as_view(), name='report-suspicious-activity'),
] + router.urls
