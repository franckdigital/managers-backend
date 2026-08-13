from django.contrib import admin

from apps.certificates.models import Certificate, CertificateTemplate


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'is_default')


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('certificate_number', 'user', 'course', 'path', 'issued_at', 'is_revoked')
    list_filter = ('is_revoked',)
    search_fields = ('certificate_number', 'verification_code', 'user__email')
