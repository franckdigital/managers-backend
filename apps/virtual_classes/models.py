from django.db import models

from apps.core.models import TimeStampedModel


class VirtualClass(TimeStampedModel):
    PROVIDER_ZOOM = 'zoom'
    PROVIDER_TEAMS = 'teams'
    PROVIDER_MEET = 'meet'
    PROVIDER_JITSI = 'jitsi'
    PROVIDER_BBB = 'bbb'
    PROVIDER_INTERNAL = 'internal'
    PROVIDER_CHOICES = [
        (PROVIDER_ZOOM, 'Zoom'), (PROVIDER_TEAMS, 'Microsoft Teams'), (PROVIDER_MEET, 'Google Meet'),
        (PROVIDER_JITSI, 'Jitsi'), (PROVIDER_BBB, 'BigBlueButton'), (PROVIDER_INTERNAL, 'Live intégré'),
    ]

    session = models.OneToOneField(
        'learning_paths.TrainingSession', on_delete=models.CASCADE, null=True, blank=True, related_name='virtual_class'
    )
    chapter = models.ForeignKey(
        'courses.Chapter', on_delete=models.SET_NULL, null=True, blank=True, related_name='virtual_classes',
        help_text='Si renseigné, la présence à cette classe peut conditionner le déverrouillage du chapitre suivant (§24.2)',
    )
    company = models.ForeignKey('tenants.Company', on_delete=models.CASCADE, null=True, blank=True, related_name='virtual_classes')
    title = models.CharField(max_length=255)
    provider = models.CharField(max_length=10, choices=PROVIDER_CHOICES, default=PROVIDER_JITSI)
    join_url = models.URLField(blank=True)
    host_url = models.URLField(blank=True)
    meeting_id = models.CharField(max_length=150, blank=True)
    passcode = models.CharField(max_length=50, blank=True)
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    recording_url = models.URLField(blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='+')

    class Meta:
        ordering = ['-scheduled_start']

    def __str__(self):
        return self.title


class VirtualClassAttendance(TimeStampedModel):
    virtual_class = models.ForeignKey(VirtualClass, on_delete=models.CASCADE, related_name='attendances')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='virtual_class_attendances')
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('virtual_class', 'user')

    def __str__(self):
        return f'{self.user} – {self.virtual_class}'


class AttendanceSignature(TimeStampedModel):
    """§24.2 — signature électronique d'une attestation de présence."""

    virtual_class = models.ForeignKey(VirtualClass, on_delete=models.CASCADE, related_name='attendance_signatures')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='attendance_signatures')
    signed_name = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    signature_hash = models.CharField(max_length=128)
    signed_at = models.DateTimeField()

    class Meta:
        unique_together = ('virtual_class', 'user')

    def __str__(self):
        return f'Attestation {self.user} – {self.virtual_class}'


class VirtualClassQuestion(TimeStampedModel):
    """Q&A raised during a virtual class, for the trainer to answer (cahier §3 Formateur)."""

    virtual_class = models.ForeignKey(VirtualClass, on_delete=models.CASCADE, related_name='questions')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='+')
    question = models.TextField()
    answer = models.TextField(blank=True)
    answered_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    answered_at = models.DateTimeField(null=True, blank=True)
