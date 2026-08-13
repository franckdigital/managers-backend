from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.notifications.views import NotificationPreferenceView, NotificationTemplateViewSet, NotificationViewSet

router = DefaultRouter()
router.register('templates', NotificationTemplateViewSet, basename='notification-template')
router.register('notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('preferences/', NotificationPreferenceView.as_view(), name='notification-preferences'),
] + router.urls
