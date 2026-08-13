from rest_framework import serializers

from apps.virtual_classes.models import AttendanceSignature, VirtualClass, VirtualClassAttendance, VirtualClassQuestion


class VirtualClassAttendanceSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = VirtualClassAttendance
        fields = '__all__'


class AttendanceSignatureSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = AttendanceSignature
        fields = '__all__'
        read_only_fields = ('user', 'ip_address', 'signature_hash', 'signed_at')


class SignAttendanceRequestSerializer(serializers.Serializer):
    signed_name = serializers.CharField(max_length=255)


class VirtualClassQuestionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = VirtualClassQuestion
        fields = '__all__'
        read_only_fields = ('user', 'answered_by', 'answered_at')


class VirtualClassSerializer(serializers.ModelSerializer):
    attendances = VirtualClassAttendanceSerializer(many=True, read_only=True)
    questions = VirtualClassQuestionSerializer(many=True, read_only=True)
    attendance_signatures = AttendanceSignatureSerializer(many=True, read_only=True)

    class Meta:
        model = VirtualClass
        fields = '__all__'
        read_only_fields = ('created_by',)
