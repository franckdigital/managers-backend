from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.constants import Roles
from apps.core.models import AuditLog, PlatformSettings
from apps.core.permissions import HasRole, IsSuperAdmin
from apps.core.serializers import AuditLogSerializer, PlatformSettingsSerializer

IsAuditViewer = HasRole.for_roles(Roles.SUPER_ADMIN, Roles.COMPANY_ADMIN)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuditViewer]
    filterset_fields = ['action', 'model_name', 'user', 'company']

    def get_queryset(self):
        user = self.request.user
        qs = AuditLog.objects.select_related('user', 'company')
        if user.is_superuser or user.role == Roles.SUPER_ADMIN:
            return qs
        return qs.filter(company_id=user.company_id)


class PlatformSettingsView(APIView):
    """Singleton settings — readable by anyone (needed for public signup/currency display),
    writable only by the super admin."""

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [IsSuperAdmin()]

    def get(self, request):
        return Response(PlatformSettingsSerializer(PlatformSettings.get_solo()).data)

    def patch(self, request):
        settings_obj = PlatformSettings.get_solo()
        serializer = PlatformSettingsSerializer(settings_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
