from django.db import models
from django.utils.text import slugify

from apps.core.models import TimeStampedModel


class SubscriptionPlan(TimeStampedModel):
    PLAN_TYPE_B2C = 'b2c'
    PLAN_TYPE_ENTERPRISE = 'enterprise'
    PLAN_TYPE_CHOICES = [
        (PLAN_TYPE_B2C, 'Centre de formation (B2C)'),
        (PLAN_TYPE_ENTERPRISE, 'Entreprise'),
    ]

    BILLING_MONTHLY = 'monthly'
    BILLING_QUARTERLY = 'quarterly'
    BILLING_SEMI_ANNUAL = 'semi_annual'
    BILLING_YEARLY = 'yearly'
    BILLING_CHOICES = [
        (BILLING_MONTHLY, '1 mois'),
        (BILLING_QUARTERLY, '3 mois'),
        (BILLING_SEMI_ANNUAL, '6 mois'),
        (BILLING_YEARLY, '12 mois (1 an)'),
    ]

    name = models.CharField(max_length=100)
    code = models.SlugField(max_length=100, unique=True)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPE_CHOICES, default=PLAN_TYPE_ENTERPRISE)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='XOF')
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CHOICES, default=BILLING_MONTHLY)
    max_users = models.PositiveIntegerField(default=50)
    max_storage_gb = models.PositiveIntegerField(default=10)
    features = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Company(TimeStampedModel):
    STATUS_TRIAL = 'trial'
    STATUS_ACTIVE = 'active'
    STATUS_SUSPENDED = 'suspended'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_TRIAL, 'Essai'),
        (STATUS_ACTIVE, 'Actif'),
        (STATUS_SUSPENDED, 'Suspendu'),
        (STATUS_CANCELLED, 'Annulé'),
    ]

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    legal_name = models.CharField(max_length=255, blank=True)
    sector = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=120, blank=True)
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to='companies/logos/', null=True, blank=True)

    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name='companies')
    subscription_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_TRIAL)
    subscription_start = models.DateField(null=True, blank=True)
    subscription_end = models.DateField(null=True, blank=True)

    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subsidiaries'
    )

    is_active = models.BooleanField(default=True)

    def get_descendant_ids(self):
        """Return this company's id plus the ids of all its subsidiaries, recursively."""
        ids = {self.id}
        for child in self.subsidiaries.all():
            ids |= child.get_descendant_ids()
        return ids

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            i = 1
            while Company.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f'{base_slug}-{i}'
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class CompanySubscription(TimeStampedModel):
    """History of subscription changes for a company (renewals, upgrades, downgrades)."""

    STATUS_ACTIVE = 'active'
    STATUS_EXPIRED = 'expired'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [(STATUS_ACTIVE, 'Active'), (STATUS_EXPIRED, 'Expirée'), (STATUS_CANCELLED, 'Annulée')]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    start_date = models.DateField()
    end_date = models.DateField()
    auto_renew = models.BooleanField(default=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f'{self.company} – {self.plan} ({self.status})'


class Department(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=30, blank=True)

    class Meta:
        unique_together = ('company', 'name')

    def __str__(self):
        return f'{self.name} ({self.company})'


class Service(TimeStampedModel):
    """A 'service' is a sub-unit of a department, per the cahier des charges (lot 1)."""

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='services')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=150)

    class Meta:
        unique_together = ('department', 'name')

    def __str__(self):
        return f'{self.name} ({self.department})'


class Team(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='teams')
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True, related_name='teams')
    name = models.CharField(max_length=150)
    manager = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_teams'
    )

    def __str__(self):
        return self.name


class UserSubscription(TimeStampedModel):
    """Individual (B2C) subscription — grants a single learner access to the full catalogue."""

    STATUS_ACTIVE = 'active'
    STATUS_EXPIRED = 'expired'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_EXPIRED, 'Expirée'),
        (STATUS_CANCELLED, 'Annulée'),
    ]

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='user_subscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    start_date = models.DateField()
    end_date = models.DateField()
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f'{self.user} – {self.plan} ({self.status})'
