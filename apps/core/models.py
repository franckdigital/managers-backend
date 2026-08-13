import uuid

from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']


class UUIDPKModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TenantQuerySet(models.QuerySet):
    def for_company(self, company):
        if company is None:
            return self
        return self.filter(company=company)


class TenantManager(models.Manager):
    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)


class CompanyScopedModel(TimeStampedModel):
    """company=None marks a record as belonging to the public B2C marketplace rather than a tenant."""

    company = models.ForeignKey(
        'tenants.Company',
        on_delete=models.CASCADE,
        related_name='%(class)s_set',
        null=True,
        blank=True,
    )

    objects = TenantManager()

    class Meta:
        abstract = True


class PlatformSettings(models.Model):
    """Singleton (always pk=1) — global platform configuration managed by the super admin."""

    platform_name = models.CharField(max_length=150, default='LMS PRO')
    support_email = models.EmailField(blank=True)
    default_currency = models.CharField(max_length=3, default='XOF')
    default_commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=30,
        help_text='Pourcentage prélevé par la plateforme sur les ventes de cours des formateurs (%)',
    )
    b2c_signup_enabled = models.BooleanField(default=True)
    featured_course_ids = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Paramètres plateforme'
        verbose_name_plural = 'Paramètres plateforme'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'Paramètres plateforme'


class AuditLog(models.Model):
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_CHOICES = [
        (ACTION_CREATE, 'Création'),
        (ACTION_UPDATE, 'Modification'),
        (ACTION_DELETE, 'Suppression'),
    ]

    user = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs'
    )
    company = models.ForeignKey(
        'tenants.Company', on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs'
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=64)
    object_repr = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.action}:{self.model_name}#{self.object_id}'
