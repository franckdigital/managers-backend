from rest_framework import serializers

from apps.certificates.models import Certificate, CertificateTemplate


class CertificateTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CertificateTemplate
        fields = '__all__'


class CertificateSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True, default=None)
    path_title = serializers.CharField(source='path.title', read_only=True, default=None)

    class Meta:
        model = Certificate
        fields = '__all__'
        read_only_fields = (
            'certificate_number', 'verification_code', 'digital_signature', 'pdf_file', 'qr_code_image', 'issued_at',
        )


class CertificateVerificationSerializer(serializers.Serializer):
    is_authentic = serializers.BooleanField()
    certificate = CertificateSerializer()
