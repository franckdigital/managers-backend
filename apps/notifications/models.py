from django.db import models

from apps.core.models import TimeStampedModel


class NotificationTemplate(TimeStampedModel):
    CHANNEL_EMAIL = 'email'
    CHANNEL_SMS = 'sms'
    CHANNEL_WHATSAPP = 'whatsapp'
    CHANNEL_PUSH = 'push'
    CHANNEL_IN_APP = 'in_app'
    CHANNEL_CHOICES = [
        (CHANNEL_EMAIL, 'Email'), (CHANNEL_SMS, 'SMS'), (CHANNEL_WHATSAPP, 'WhatsApp'),
        (CHANNEL_PUSH, 'Push'), (CHANNEL_IN_APP, 'In-App'),
    ]

    code = models.CharField(max_length=100, unique=True)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    subject = models.CharField(max_length=255, blank=True)
    body_template = models.TextField(help_text='Variables: {{full_name}}, {{course_title}}, etc.')

    def __str__(self):
        return self.code


class NotificationPreference(TimeStampedModel):
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='notification_preference')
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    whatsapp_enabled = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=True)
    in_app_enabled = models.BooleanField(default=True)


class Notification(TimeStampedModel):
    CHANNEL_EMAIL = 'email'
    CHANNEL_SMS = 'sms'
    CHANNEL_WHATSAPP = 'whatsapp'
    CHANNEL_PUSH = 'push'
    CHANNEL_IN_APP = 'in_app'
    CHANNEL_CHOICES = [
        (CHANNEL_EMAIL, 'Email'), (CHANNEL_SMS, 'SMS'), (CHANNEL_WHATSAPP, 'WhatsApp'),
        (CHANNEL_PUSH, 'Push'), (CHANNEL_IN_APP, 'In-App'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_SENT = 'sent'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [(STATUS_PENDING, 'En attente'), (STATUS_SENT, 'Envoyée'), (STATUS_FAILED, 'Échouée')]

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='notifications')
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} – {self.title} ({self.channel})'
