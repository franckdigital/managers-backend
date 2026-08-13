from django.contrib import admin

from apps.content_security.models import AccessLog, HLSPackage, SuspiciousActivityEvent


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'path', 'method', 'ip_address', 'status_code', 'created_at')
    list_filter = ('method', 'status_code')
    search_fields = ('user__email', 'path', 'ip_address')


@admin.register(HLSPackage)
class HLSPackageAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'status', 'segment_count', 'segment_duration_seconds')
    list_filter = ('status',)
    readonly_fields = ('encryption_key_hex', 'encryption_iv_hex')


@admin.register(SuspiciousActivityEvent)
class SuspiciousActivityEventAdmin(admin.ModelAdmin):
    list_display = ('user', 'event_type', 'lesson', 'ip_address', 'created_at')
    list_filter = ('event_type',)
    search_fields = ('user__email', 'ip_address')
