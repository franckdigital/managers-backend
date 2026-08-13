from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.core.views import AuditLogViewSet, PlatformSettingsView

router = DefaultRouter()
router.register('audit-logs', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('platform-settings/', PlatformSettingsView.as_view(), name='platform-settings'),
] + router.urls
