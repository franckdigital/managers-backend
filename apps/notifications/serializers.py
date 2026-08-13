from rest_framework import serializers

from apps.notifications.models import Notification, NotificationPreference, NotificationTemplate


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = '__all__'


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = '__all__'
        read_only_fields = ('user',)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ('user', 'channel', 'title', 'message', 'data', 'status', 'sent_at')
