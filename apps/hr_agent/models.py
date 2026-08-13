from django.db import models

from apps.core.models import TimeStampedModel


class AgentResource(TimeStampedModel):
    """Un contenu que l'agent IA RH peut proposer à un employé — texte, PDF téléchargeable
    ou vidéo — organisé par catégorie et, pour l'intégration, par département/service."""

    CATEGORY_INTERNAL_RULES = 'reglement_interieur'
    CATEGORY_ONBOARDING = 'onboarding'
    CATEGORY_GENERAL = 'general'
    CATEGORY_CHOICES = [
        (CATEGORY_INTERNAL_RULES, "Règlement intérieur"),
        (CATEGORY_ONBOARDING, "Intégration / Onboarding"),
        (CATEGORY_GENERAL, "Information générale"),
    ]

    TYPE_TEXT = 'text'
    TYPE_PDF = 'pdf'
    TYPE_VIDEO = 'video'
    TYPE_CHOICES = [
        (TYPE_TEXT, 'Texte'),
        (TYPE_PDF, 'Document PDF'),
        (TYPE_VIDEO, 'Vidéo'),
    ]

    company = models.ForeignKey(
        'tenants.Company', on_delete=models.CASCADE, null=True, blank=True, related_name='agent_resources',
    )
    department = models.ForeignKey(
        'tenants.Department', on_delete=models.CASCADE, null=True, blank=True, related_name='agent_resources',
        help_text="Laisser vide pour un contenu valable dans toute l'entreprise (ex: règlement intérieur).",
    )
    service = models.ForeignKey(
        'tenants.Service', on_delete=models.CASCADE, null=True, blank=True, related_name='agent_resources',
    )

    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default=CATEGORY_GENERAL)
    content_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_TEXT)
    title = models.CharField(max_length=255)
    text_body = models.TextField(blank=True)
    file = models.FileField(upload_to='hr_agent/documents/', null=True, blank=True)
    video_url = models.URLField(blank=True)
    keywords = models.CharField(
        max_length=500, blank=True,
        help_text="Mots-clés séparés par des virgules, utilisés par l'agent pour retrouver ce contenu.",
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    class Meta:
        ordering = ['category', 'order', '-created_at']

    def __str__(self):
        return self.title


class AgentConversation(TimeStampedModel):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='hr_agent_conversations')

    class Meta:
        ordering = ['-updated_at']


class AgentMessage(TimeStampedModel):
    ROLE_USER = 'user'
    ROLE_AGENT = 'agent'
    ROLE_CHOICES = [(ROLE_USER, 'Utilisateur'), (ROLE_AGENT, 'Agent')]

    conversation = models.ForeignKey(AgentConversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField(blank=True)
    resources = models.ManyToManyField(AgentResource, blank=True, related_name='+')
    intent = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ['created_at']


class JobDescriptionRequest(TimeStampedModel):
    """Trace des fiches de poste générées à la demande via l'agent IA."""

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='job_description_requests')
    full_name = models.CharField(max_length=255)
    job_title = models.CharField(max_length=255)
    department_name = models.CharField(max_length=255, blank=True)
    manager_name = models.CharField(max_length=255, blank=True)
    start_date = models.DateField(null=True, blank=True)
    missions = models.JSONField(default=list, blank=True)
    pdf_file = models.FileField(upload_to='hr_agent/fiches_poste/', null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Fiche de poste — {self.full_name} ({self.job_title})'
