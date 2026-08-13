from rest_framework import serializers

from apps.content_security.models import AccessLog, HLSPackage, SuspiciousActivityEvent


class AccessLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessLog
        fields = '__all__'


class HLSPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HLSPackage
        exclude = ('encryption_key_hex', 'encryption_iv_hex')


class SuspiciousActivityEventSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = SuspiciousActivityEvent
        fields = '__all__'
        read_only_fields = ('user', 'ip_address', 'user_agent')
