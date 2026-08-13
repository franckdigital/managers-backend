from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel


class CourseProgressionSettings(TimeStampedModel):
    """Per-course progression policy — cahier des charges §26."""

    course = models.OneToOneField('courses.Course', on_delete=models.CASCADE, related_name='progression_settings')

    sequential_enabled = models.BooleanField(default=True)
    min_video_watch_percent = models.PositiveSmallIntegerField(
        default=80, validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    min_watch_time_seconds = models.PositiveIntegerField(null=True, blank=True)
    quiz_required = models.BooleanField(default=True)
    min_passing_score = models.DecimalField(max_digits=5, decimal_places=2, default=70)
    trainer_validation_required = models.BooleanField(default=False)
    manager_hr_validation_required = models.BooleanField(default=False)
    virtual_class_attendance_required = models.BooleanField(default=False)
    attendance_signature_required = models.BooleanField(default=False)
    max_attempts = models.PositiveIntegerField(null=True, blank=True)
    certificate_requires_full_completion = models.BooleanField(default=True)

    download_videos_allowed = models.BooleanField(default=False)
    download_documents_allowed = models.BooleanField(default=False)
    offline_access_allowed = models.BooleanField(default=False)

    def __str__(self):
        return f'Politique de progression – {self.course}'


class LessonProgress(TimeStampedModel):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='lesson_progresses')
    lesson = models.ForeignKey('courses.Lesson', on_delete=models.CASCADE, related_name='progresses')

    is_completed = models.BooleanField(default=False)
    watch_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    watched_seconds = models.PositiveIntegerField(default=0, help_text='Position maximale atteinte')
    last_position_seconds = models.PositiveIntegerField(default=0, help_text='Position exacte de reprise')
    document_viewed = models.BooleanField(default=False)
    time_spent_seconds = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Tracking des interactions
    open_count = models.PositiveIntegerField(default=0, help_text='Nombre de fois que la leçon a été ouverte')
    video_play_count = models.PositiveIntegerField(default=0, help_text='Nombre de fois que la vidéo a été lancée')
    last_opened_at = models.DateTimeField(null=True, blank=True, help_text='Dernière ouverture de la leçon')

    class Meta:
        unique_together = ('user', 'lesson')

    def __str__(self):
        return f'{self.user} – {self.lesson}'


class CourseView(TimeStampedModel):
    """Comptabilise les ouvertures de page cours par utilisateur."""

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='course_views')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='user_views')
    open_count = models.PositiveIntegerField(default=1, help_text='Nombre de fois que la page cours a été ouverte')
    last_opened_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f'{self.user} – {self.course} ({self.open_count} ouvertures)'


class ChapterUnlock(TimeStampedModel):
    """Audit record of the moment a chapter became accessible to a learner."""

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='chapter_unlocks')
    chapter = models.ForeignKey('courses.Chapter', on_delete=models.CASCADE, related_name='unlocks')
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'chapter')


class ChapterValidation(TimeStampedModel):
    """§24.2 — manual unlock condition: trainer/manager/HR sign-off required to proceed."""

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='chapter_validations')
    chapter = models.ForeignKey('courses.Chapter', on_delete=models.CASCADE, related_name='validations')
    validated_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='+')
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ('user', 'chapter')


class XAPIStatement(TimeStampedModel):
    """Minimal Learning Record Store (LRS) compatible with the xAPI actor/verb/object model
    (cahier de positionnement §23)."""

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='xapi_statements')
    verb = models.CharField(max_length=100)
    object_type = models.CharField(max_length=50, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    result = models.JSONField(default=dict, blank=True)
    raw_statement = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
