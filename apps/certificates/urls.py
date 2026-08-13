from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.certificates.views import CertificateTemplateViewSet, CertificateViewSet, VerifyCertificateView

router = DefaultRouter()
router.register('certificate-templates', CertificateTemplateViewSet, basename='certificate-template')
router.register('certificates', CertificateViewSet, basename='certificate')

urlpatterns = [
    path('verify/<str:verification_code>/', VerifyCertificateView.as_view(), name='verify-certificate'),
] + router.urls
