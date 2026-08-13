from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.accounts.managers import UserManager
from apps.core.constants import Roles
from apps.core.models import TimeStampedModel


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)

    role = models.CharField(max_length=30, choices=Roles.CHOICES, default=Roles.STUDENT)
    company = models.ForeignKey(
        'tenants.Company', on_delete=models.SET_NULL, null=True, blank=True, related_name='users'
    )
    department = models.ForeignKey(
        'tenants.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='members'
    )
    service = models.ForeignKey(
        'tenants.Service', on_delete=models.SET_NULL, null=True, blank=True, related_name='members'
    )
    team = models.ForeignKey('tenants.Team', on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    manager = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='direct_reports'
    )

    phone = models.CharField(max_length=30, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    employee_id = models.CharField(max_length=50, blank=True)
    job_title = models.CharField(max_length=150, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    country = models.CharField(max_length=120, blank=True)
    bio = models.TextField(blank=True)

    is_trainer_approved = models.BooleanField(default=False)
    payout_method = models.CharField(
        max_length=20,
        choices=[('bank_transfer', 'Virement bancaire'), ('mobile_money', 'Mobile Money')],
        blank=True,
        help_text='Formateurs uniquement — méthode de versement des revenus',
    )
    bank_account_name = models.CharField(max_length=150, blank=True)
    bank_iban = models.CharField(max_length=50, blank=True)
    is_premium = models.BooleanField(default=False, help_text='§25.3 — profil Premium B2C, utilisé pour restreindre certains téléchargements')
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=64, blank=True)
    last_active_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.get_full_name() or self.email

    @property
    def is_b2b(self):
        return self.company_id is not None

    def has_perm_code(self, code):
        if self.is_superuser or self.role == Roles.SUPER_ADMIN:
            return True
        return RolePermission.objects.filter(role=self.role, permission__code=code).exists()


class PermissionCode(TimeStampedModel):
    code = models.CharField(max_length=100, unique=True)
    label = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.code


class RolePermission(models.Model):
    role = models.CharField(max_length=50)
    permission = models.ForeignKey(PermissionCode, on_delete=models.CASCADE, related_name='role_links')

    class Meta:
        unique_together = ('role', 'permission')

    def __str__(self):
        return f'{self.role} -> {self.permission.code}'


class RoleDefinition(TimeStampedModel):
    """System and custom roles. System roles mirror Roles.CHOICES; custom roles are
    enterprise-specific and managed by super_admin."""
    key   = models.CharField(max_length=50, unique=True)
    label = models.CharField(max_length=100)
    color = models.CharField(max_length=20, default='slate', blank=True)
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_system', 'key']

    def __str__(self):
        return self.label


class UserDevice(TimeStampedModel):
    """Tracks active sessions per user to enforce the concurrent-device limit (cahier des charges §25.4)."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices')
    device_id = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    refresh_token_jti = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'device_id')
        ordering = ['-last_seen']

    def __str__(self):
        return f'{self.user} – {self.device_id[:12]}'


class EmployeeImportBatch(TimeStampedModel):
    """Audit trail for bulk employee imports (CSV) performed by a company admin (§3 Administrateur Entreprise)."""

    STATUS_PENDING = 'pending'
    STATUS_DONE = 'done'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [(STATUS_PENDING, 'En cours'), (STATUS_DONE, 'Terminé'), (STATUS_FAILED, 'Échoué')]

    company = models.ForeignKey('tenants.Company', on_delete=models.CASCADE, related_name='employee_import_batches')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')
    file = models.FileField(upload_to='employee_imports/')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    total_rows = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f'Import {self.company} – {self.created_at:%Y-%m-%d}'
