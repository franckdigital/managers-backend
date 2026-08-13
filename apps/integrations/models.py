import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.db import models

from apps.core.models import TimeStampedModel


class APIClient(TimeStampedModel):
    """Public API access credentials for third-party integrations (cahier §10)."""

    company = models.ForeignKey('tenants.Company', on_delete=models.CASCADE, null=True, blank=True, related_name='api_clients')
    name = models.CharField(max_length=150)
    api_key = models.CharField(max_length=64, unique=True, editable=False)
    api_secret_hash = models.CharField(max_length=255, editable=False)
    scopes = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='+')

    def save(self, *args, **kwargs):
        if not self.api_key:
            self.api_key = secrets.token_hex(16)
        super().save(*args, **kwargs)

    def set_secret(self, raw_secret):
        self.api_secret_hash = make_password(raw_secret)

    def check_secret(self, raw_secret):
        return check_password(raw_secret, self.api_secret_hash)

    def __str__(self):
        return self.name


class WebhookEndpoint(TimeStampedModel):
    company = models.ForeignKey('tenants.Company', on_delete=models.CASCADE, null=True, blank=True, related_name='webhook_endpoints')
    url = models.URLField()
    secret = models.CharField(max_length=64, blank=True)
    events = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.secret:
            self.secret = secrets.token_hex(20)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.url


class WebhookDelivery(TimeStampedModel):
    endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name='deliveries')
    event_type = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    response_status = models.PositiveIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    success = models.BooleanField(default=False)
    attempt_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']


class ERPConnector(TimeStampedModel):
    PROVIDER_SAGE = 'sage'
    PROVIDER_ODOO = 'odoo'
    PROVIDER_SAP = 'sap'
    PROVIDER_ORACLE = 'oracle'
    PROVIDER_WORKDAY = 'workday'
    PROVIDER_CHOICES = [
        (PROVIDER_SAGE, 'Sage'), (PROVIDER_ODOO, 'Odoo'), (PROVIDER_SAP, 'SAP'),
        (PROVIDER_ORACLE, 'Oracle'), (PROVIDER_WORKDAY, 'Workday'),
    ]

    company = models.ForeignKey('tenants.Company', on_delete=models.CASCADE, related_name='erp_connectors')
    provider = models.CharField(max_length=15, choices=PROVIDER_CHOICES)
    config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_sync_status = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ('company', 'provider')

    def __str__(self):
        return f'{self.company} – {self.provider}'


class SSOConfiguration(TimeStampedModel):
    PROVIDER_AZURE_AD = 'azure_ad'
    PROVIDER_GOOGLE_WORKSPACE = 'google_workspace'
    PROVIDER_GENERIC_OAUTH = 'generic_oauth'
    PROVIDER_CHOICES = [
        (PROVIDER_AZURE_AD, 'Azure AD'), (PROVIDER_GOOGLE_WORKSPACE, 'Google Workspace'),
        (PROVIDER_GENERIC_OAUTH, 'OAuth2 générique'),
    ]

    company = models.OneToOneField('tenants.Company', on_delete=models.CASCADE, related_name='sso_configuration')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    client_id = models.CharField(max_length=255, blank=True)
    client_secret = models.CharField(max_length=255, blank=True)
    tenant_id = models.CharField(max_length=255, blank=True)
    authorization_url = models.URLField(blank=True)
    token_url = models.URLField(blank=True)
    userinfo_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.company} – {self.provider}'
