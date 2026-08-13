from apps.core.audit import log_audit
from apps.core.constants import Roles
from apps.core.models import AuditLog


class CompanyScopedViewSetMixin:
    """Restricts a viewset's queryset to the requesting user's company tree (row-level multi-tenancy).
    Super admins and platform staff see everything; everyone else is scoped to their own company plus
    any subsidiaries of that company. An optional `?company=<id>` query param lets a parent-company user
    drill down to one specific company in their tree (rejected if outside that tree)."""

    company_field = 'company'

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return qs.none()
        if user.is_superuser or getattr(user, 'role', None) == Roles.SUPER_ADMIN:
            return qs
        company = getattr(user, 'company', None)
        if company is None:
            return qs.none()
        allowed_ids = company.get_descendant_ids()
        requested = self.request.query_params.get('company')
        if requested:
            try:
                requested_id = int(requested)
            except (TypeError, ValueError):
                return qs.none()
            if requested_id not in allowed_ids:
                return qs.none()
            allowed_ids = {requested_id}
        return qs.filter(**{f'{self.company_field}__in': allowed_ids})

    def perform_create(self, serializer):
        user = self.request.user
        save_kwargs = {}
        if self.company_field not in serializer.validated_data and hasattr(user, 'company_id'):
            save_kwargs[self.company_field] = user.company
        serializer.save(**save_kwargs)


class AuditLogMixin:
    """Records create/update/delete on sensitive viewsets to AuditLog for traceability."""

    def perform_create(self, serializer):
        super().perform_create(serializer)
        log_audit(self.request.user, AuditLog.ACTION_CREATE, serializer.instance, request=self.request)

    def perform_update(self, serializer):
        changes = {field: str(value) for field, value in serializer.validated_data.items()}
        super().perform_update(serializer)
        log_audit(self.request.user, AuditLog.ACTION_UPDATE, serializer.instance, changes=changes, request=self.request)

    def perform_destroy(self, instance):
        log_audit(self.request.user, AuditLog.ACTION_DELETE, instance, request=self.request)
        super().perform_destroy(instance)
