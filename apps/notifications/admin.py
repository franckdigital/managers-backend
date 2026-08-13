from django.contrib import admin

from apps.notifications.models import Notification, NotificationPreference, NotificationTemplate


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ('code', 'channel', 'subject')
    list_filter = ('channel',)


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_enabled', 'sms_enabled', 'whatsapp_enabled', 'push_enabled', 'in_app_enabled')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'channel', 'title', 'status', 'is_read', 'created_at')
    list_filter = ('channel', 'status', 'is_read')
    search_fields = ('user__email', 'title')
