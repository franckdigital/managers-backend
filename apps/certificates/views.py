from django.http import HttpResponse
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.certificates.models import Certificate, CertificateTemplate
from apps.certificates.serializers import CertificateSerializer, CertificateTemplateSerializer
from apps.certificates.services import build_preview_pdf, regenerate_all_certificates, verify_certificate
from apps.core.constants import Roles
from apps.core.mixins import CompanyScopedViewSetMixin
from apps.core.permissions import IsCompanyAdmin, _role


class CertificateTemplateViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = CertificateTemplate.objects.all()
    serializer_class = CertificateTemplateSerializer
    permission_classes = [IsCompanyAdmin]
    company_field = 'company'

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_superuser or _role(self.request) == Roles.SUPER_ADMIN:
            if CertificateTemplate.objects.filter(company__isnull=True).exists():
                raise ValidationError('Le template global existe déjà.')
            serializer.save(company=None, is_default=True)
        else:
            if CertificateTemplate.objects.filter(company=user.company).exists():
                raise ValidationError('Cette entreprise a déjà un template.')
            serializer.save(company=user.company, is_default=False)
        regenerate_all_certificates()

    def perform_update(self, serializer):
        serializer.save()
        regenerate_all_certificates()

    def perform_destroy(self, instance):
        instance.delete()
        regenerate_all_certificates()

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        template = self.get_object()
        pdf_bytes = build_preview_pdf(template)
        return HttpResponse(pdf_bytes, content_type='application/pdf')


class CertificateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CertificateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['course', 'path', 'is_revoked']

    def get_queryset(self):
        user = self.request.user
        qs = Certificate.objects.select_related('user', 'course', 'path')
        if user.is_superuser or user.role in (Roles.SUPER_ADMIN, Roles.COMPANY_ADMIN, Roles.HR):
            return qs
        return qs.filter(user=user)


class VerifyCertificateView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, verification_code):
        result = verify_certificate(verification_code)
        if result is None:
            return Response({'detail': 'Certificat introuvable.'}, status=404)
        certificate, is_authentic = result
        return Response({'is_authentic': is_authentic, 'certificate': CertificateSerializer(certificate).data})
