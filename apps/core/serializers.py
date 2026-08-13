from rest_framework import serializers

from apps.core.models import AuditLog, PlatformSettings


class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True, default='')

    class Meta:
        model = AuditLog
        fields = '__all__'


class PlatformSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSettings
        fields = '__all__'
