from django.contrib import admin

from apps.core.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'company', 'action', 'model_name', 'object_id')
    list_filter = ('action', 'model_name')
    search_fields = ('object_id', 'object_repr')
    readonly_fields = [f.name for f in AuditLog._meta.fields]
