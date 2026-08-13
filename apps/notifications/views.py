from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsSuperAdmin
from apps.notifications.models import Notification, NotificationPreference, NotificationTemplate
from apps.notifications.serializers import (
    NotificationPreferenceSerializer,
    NotificationSerializer,
    NotificationTemplateSerializer,
)


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsSuperAdmin]


class NotificationPreferenceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        preference, _ = NotificationPreference.objects.get_or_create(user=request.user)
        return Response(NotificationPreferenceSerializer(preference).data)

    def patch(self, request):
        preference, _ = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceSerializer(preference, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['channel', 'is_read', 'status']
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=['is_read', 'read_at'])
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        self.get_queryset().filter(is_read=False).update(is_read=True, read_at=timezone.now())
        return Response({'detail': 'ok'})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        return Response({'count': self.get_queryset().filter(is_read=False).count()})
