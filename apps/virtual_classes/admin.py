from django.contrib import admin

from apps.virtual_classes.models import AttendanceSignature, VirtualClass, VirtualClassAttendance, VirtualClassQuestion


class VirtualClassAttendanceInline(admin.TabularInline):
    model = VirtualClassAttendance
    extra = 0


class AttendanceSignatureInline(admin.TabularInline):
    model = AttendanceSignature
    extra = 0
    readonly_fields = ('signature_hash', 'signed_at')


@admin.register(VirtualClass)
class VirtualClassAdmin(admin.ModelAdmin):
    list_display = ('title', 'provider', 'chapter', 'company', 'scheduled_start', 'scheduled_end')
    list_filter = ('provider',)
    inlines = [VirtualClassAttendanceInline, AttendanceSignatureInline]


@admin.register(VirtualClassQuestion)
class VirtualClassQuestionAdmin(admin.ModelAdmin):
    list_display = ('virtual_class', 'user', 'answered_at')


@admin.register(AttendanceSignature)
class AttendanceSignatureAdmin(admin.ModelAdmin):
    list_display = ('virtual_class', 'user', 'signed_name', 'signed_at')
    readonly_fields = ('signature_hash',)
