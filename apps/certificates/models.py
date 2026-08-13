from django.db import models

from apps.core.models import TimeStampedModel


class CertificateTemplate(TimeStampedModel):
    company = models.ForeignKey('tenants.Company', on_delete=models.CASCADE, null=True, blank=True, related_name='certificate_templates')
    name = models.CharField(max_length=150)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # En-tete / branding
    org_name = models.CharField(max_length=150, blank=True)
    org_name_font_size = models.PositiveSmallIntegerField(default=15)
    org_logo = models.ImageField(upload_to='certificates/templates/logos/', null=True, blank=True)
    accent_color = models.CharField(max_length=7, default='#0F4C81')

    # Contenu (placeholders substitues a la generation : {recipient_name} {course_title} {date} {certificate_number} {org_name})
    title_text = models.CharField(max_length=150, default='CERTIFICAT DE FORMATION')
    title_font_size = models.PositiveSmallIntegerField(default=28)
    intro_text = models.CharField(max_length=150, default='Est décerné avec distinction à')
    intro_font_size = models.PositiveSmallIntegerField(default=15)
    body_paragraph = models.TextField(
        default='Pour avoir suivi avec succès la formation {course_title}, démontrant ainsi engagement et maîtrise des compétences visées.'
    )
    body_font_size = models.PositiveSmallIntegerField(default=14)
    footer_website = models.CharField(max_length=255, blank=True)

    # Signataire 1 (gauche)
    signer1_name = models.CharField(max_length=150, blank=True)
    signer1_title = models.CharField(max_length=150, blank=True)
    signer1_signature = models.ImageField(upload_to='certificates/templates/signatures/', null=True, blank=True)

    # Signataire 2 (droite)
    signer2_name = models.CharField(max_length=150, blank=True)
    signer2_title = models.CharField(max_length=150, blank=True)
    signer2_signature = models.ImageField(upload_to='certificates/templates/signatures/', null=True, blank=True)

    # Espacements verticaux supplementaires (en pt) entre les blocs du certificat
    gap_after_header = models.PositiveSmallIntegerField(default=0)
    gap_after_title = models.PositiveSmallIntegerField(default=0)
    gap_after_content = models.PositiveSmallIntegerField(default=0)

    # Image de fond plein cadre (optionnelle) : si renseignee, remplace la bordure decorative generee
    background_image = models.ImageField(upload_to='certificates/templates/', null=True, blank=True)
    layout_config = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name


class Certificate(TimeStampedModel):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='certificates')
    path = models.ForeignKey('learning_paths.LearningPath', on_delete=models.SET_NULL, null=True, blank=True, related_name='certificates')
    template = models.ForeignKey(CertificateTemplate, on_delete=models.SET_NULL, null=True, blank=True, related_name='certificates')

    certificate_number = models.CharField(max_length=50, unique=True)
    verification_code = models.CharField(max_length=64, unique=True)
    digital_signature = models.CharField(max_length=128, blank=True)

    pdf_file = models.FileField(upload_to='certificates/pdf/', null=True, blank=True)
    qr_code_image = models.ImageField(upload_to='certificates/qr/', null=True, blank=True)

    issued_at = models.DateTimeField(auto_now_add=True)
    is_revoked = models.BooleanField(default=False)

    class Meta:
        ordering = ['-issued_at']

    def __str__(self):
        return self.certificate_number
