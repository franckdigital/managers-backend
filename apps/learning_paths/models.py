from django.db import models

from apps.core.models import TimeStampedModel


class LearningPath(TimeStampedModel):
    TYPE_ONBOARDING = 'onboarding'
    TYPE_MANAGER = 'manager'
    TYPE_JOB_ROLE = 'job_role'
    TYPE_CUSTOM = 'custom'
    TYPE_CHOICES = [
        (TYPE_ONBOARDING, 'Parcours Employé (Accueil)'),
        (TYPE_MANAGER, 'Parcours Manager'),
        (TYPE_JOB_ROLE, 'Parcours Métier'),
        (TYPE_CUSTOM, 'Parcours personnalisé'),
    ]

    company = models.ForeignKey(
        'tenants.Company', on_delete=models.CASCADE, null=True, blank=True, related_name='learning_paths'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    path_type = models.CharField(max_length=15, choices=TYPE_CHOICES, default=TYPE_CUSTOM)
    target_job_title = models.CharField(max_length=150, blank=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='+')
    is_active = models.BooleanField(default=True)
    certificate_enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class LearningPathStep(TimeStampedModel):
    path = models.ForeignKey(LearningPath, on_delete=models.CASCADE, related_name='steps')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='path_steps')
    order = models.PositiveIntegerField(default=0)
    is_mandatory = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        unique_together = ('path', 'course')

    def __str__(self):
        return f'{self.path} – {self.order}. {self.course}'


class LearningPathEnrollment(TimeStampedModel):
    STATUS_NOT_STARTED = 'not_started'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES = [
        (STATUS_NOT_STARTED, 'Non démarré'), (STATUS_IN_PROGRESS, 'En cours'), (STATUS_COMPLETED, 'Terminé'),
    ]

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='path_enrollments')
    path = models.ForeignKey(LearningPath, on_delete=models.CASCADE, related_name='enrollments')
    assigned_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_NOT_STARTED)
    progress_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'path')

    def __str__(self):
        return f'{self.user} -> {self.path}'


class TrainingSession(TimeStampedModel):
    """A scheduled, calendared instance of a course or path (live cohort, classroom or virtual)."""

    LOCATION_ONLINE = 'online'
    LOCATION_ONSITE = 'onsite'
    LOCATION_CHOICES = [(LOCATION_ONLINE, 'En ligne'), (LOCATION_ONSITE, 'Présentiel')]

    company = models.ForeignKey(
        'tenants.Company', on_delete=models.CASCADE, null=True, blank=True, related_name='training_sessions'
    )
    course = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions')
    path = models.ForeignKey(LearningPath, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions')
    title = models.CharField(max_length=255)
    trainer = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='sessions_led')
    location_type = models.CharField(max_length=10, choices=LOCATION_CHOICES, default=LOCATION_ONLINE)
    address = models.CharField(max_length=255, blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    capacity = models.PositiveIntegerField(null=True, blank=True)
    join_url = models.URLField(blank=True, help_text='Lien de connexion pour les sessions en ligne')

    class Meta:
        ordering = ['start_datetime']

    def __str__(self):
        return f'{self.title} ({self.start_datetime:%Y-%m-%d %H:%M})'


class SessionParticipant(TimeStampedModel):
    STATUS_REGISTERED = 'registered'
    STATUS_ATTENDED = 'attended'
    STATUS_ABSENT = 'absent'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_REGISTERED, 'Inscrit'), (STATUS_ATTENDED, 'Présent'),
        (STATUS_ABSENT, 'Absent'), (STATUS_CANCELLED, 'Annulé'),
    ]

    session = models.ForeignKey(TrainingSession, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='session_participations')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_REGISTERED)

    class Meta:
        unique_together = ('session', 'user')
