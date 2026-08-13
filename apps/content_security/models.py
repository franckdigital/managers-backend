from django.db import models

from apps.core.models import TimeStampedModel


class AccessLog(TimeStampedModel):
    """§25.4 — journalisation des accès aux contenus protégés."""

    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='content_access_logs')
    path = models.CharField(max_length=500)
    method = models.CharField(max_length=10, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    object_type = models.CharField(max_length=50, blank=True)
    object_id = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['-created_at']


class HLSPackage(TimeStampedModel):
    """§25.2 — adaptive HLS streaming with AES-128 segment encryption ('DRM-lite').
    The raw key is stored server-side and only ever released through the signed,
    short-lived key endpoint — never embedded in the manifest itself."""

    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_READY = 'ready'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'En attente'), (STATUS_PROCESSING, 'En cours'),
        (STATUS_READY, 'Prêt'), (STATUS_FAILED, 'Échoué'),
    ]

    lesson = models.OneToOneField('courses.Lesson', on_delete=models.CASCADE, related_name='hls_package')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING)
    output_dir = models.CharField(max_length=500, blank=True, help_text='Chemin relatif sous MEDIA_ROOT')
    segment_count = models.PositiveIntegerField(default=0)
    segment_duration_seconds = models.PositiveIntegerField(default=6)
    encryption_key_hex = models.CharField(max_length=32, blank=True)
    encryption_iv_hex = models.CharField(max_length=32, blank=True)
    error_message = models.TextField(blank=True)

    def __str__(self):
        return f'HLS – {self.lesson} ({self.status})'


class SuspiciousActivityEvent(TimeStampedModel):
    """§25.5 — the frontend cannot fully prevent screenshots/screen-recording (the cahier
    says so itself), so the realistic backend contribution is to record and surface
    suspicious signals reported by the player/app: devtools opened, right-click blocked
    and bypassed, repeated tab/window blur during an exam, screen-recording API detected, etc."""

    EVENT_DEVTOOLS_OPENED = 'devtools_opened'
    EVENT_RIGHT_CLICK_BLOCKED = 'right_click_blocked'
    EVENT_COPY_ATTEMPT = 'copy_attempt'
    EVENT_DRAG_ATTEMPT = 'drag_attempt'
    EVENT_SEEK_FORWARD_BLOCKED = 'seek_forward_blocked'
    EVENT_TAB_BLUR_DURING_EXAM = 'tab_blur_during_exam'
    EVENT_SCREEN_RECORDING_SUSPECTED = 'screen_recording_suspected'
    EVENT_MULTIPLE_LOGIN_ATTEMPT = 'multiple_login_attempt'
    EVENT_OTHER = 'other'
    EVENT_CHOICES = [
        (EVENT_DEVTOOLS_OPENED, 'Outils de développement ouverts'),
        (EVENT_RIGHT_CLICK_BLOCKED, 'Clic droit bloqué'),
        (EVENT_COPY_ATTEMPT, 'Tentative de copie'),
        (EVENT_DRAG_ATTEMPT, 'Tentative de glisser-déposer'),
        (EVENT_SEEK_FORWARD_BLOCKED, 'Saut en avant bloqué'),
        (EVENT_TAB_BLUR_DURING_EXAM, "Changement d'onglet pendant un examen"),
        (EVENT_SCREEN_RECORDING_SUSPECTED, "Enregistrement d'écran suspecté"),
        (EVENT_MULTIPLE_LOGIN_ATTEMPT, 'Tentative de connexion multiple'),
        (EVENT_OTHER, 'Autre'),
    ]

    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='suspicious_events')
    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES)
    lesson = models.ForeignKey('courses.Lesson', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.event_type} – {self.user}'
