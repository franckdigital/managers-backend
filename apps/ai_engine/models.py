from django.db import models

from apps.core.models import TimeStampedModel


class AIConversation(TimeStampedModel):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='ai_conversations')
    course = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    title = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-updated_at']


class AIMessage(TimeStampedModel):
    ROLE_USER = 'user'
    ROLE_ASSISTANT = 'assistant'
    ROLE_CHOICES = [(ROLE_USER, 'Utilisateur'), (ROLE_ASSISTANT, 'Assistant')]

    conversation = models.ForeignKey(AIConversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()

    class Meta:
        ordering = ['created_at']


class AIGeneratedQuiz(TimeStampedModel):
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='+')
    chapter = models.ForeignKey('courses.Chapter', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='+')
    source_text = models.TextField(blank=True)
    generated_questions = models.JSONField(default=list)
    imported_assessment = models.ForeignKey(
        'assessments.Assessment', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )


class CourseRecommendation(TimeStampedModel):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='recommendations')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='+')
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    reason = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ('user', 'course')
        ordering = ['-score']


class DifficultyAlert(TimeStampedModel):
    SIGNAL_LOW_SCORE = 'low_score'
    SIGNAL_REPEATED_FAILURE = 'repeated_failure'
    SIGNAL_SLOW_PROGRESS = 'slow_progress'
    SIGNAL_CHOICES = [
        (SIGNAL_LOW_SCORE, 'Score faible'), (SIGNAL_REPEATED_FAILURE, 'Échecs répétés'),
        (SIGNAL_SLOW_PROGRESS, 'Progression lente'),
    ]

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='difficulty_alerts')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='+')
    signal_type = models.CharField(max_length=20, choices=SIGNAL_CHOICES)
    details = models.JSONField(default=dict, blank=True)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
