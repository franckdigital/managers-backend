from django.db import models

from apps.core.models import TimeStampedModel


class Level(TimeStampedModel):
    name = models.CharField(max_length=100)
    min_xp = models.PositiveIntegerField()
    icon = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['min_xp']

    def __str__(self):
        return self.name


class Badge(TimeStampedModel):
    CRITERIA_COURSE_COMPLETION = 'course_completion'
    CRITERIA_XP_THRESHOLD = 'xp_threshold'
    CRITERIA_STREAK = 'streak'
    CRITERIA_SKILL_MASTERY = 'skill_mastery'
    CRITERIA_CUSTOM = 'custom'
    CRITERIA_CHOICES = [
        (CRITERIA_COURSE_COMPLETION, 'Complétion de formation'), (CRITERIA_XP_THRESHOLD, "Seuil d'XP"),
        (CRITERIA_STREAK, 'Série de connexions'), (CRITERIA_SKILL_MASTERY, 'Maîtrise de compétence'),
        (CRITERIA_CUSTOM, 'Personnalisé'),
    ]

    company = models.ForeignKey('tenants.Company', on_delete=models.CASCADE, null=True, blank=True, related_name='badges')
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to='badges/', null=True, blank=True)
    criteria_type = models.CharField(max_length=20, choices=CRITERIA_CHOICES, default=CRITERIA_CUSTOM)
    criteria_value = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.title


class UserBadge(TimeStampedModel):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='awarded_to')
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'badge')


class XPLog(TimeStampedModel):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='xp_logs')
    amount = models.IntegerField()
    reason = models.CharField(max_length=255)
    source_type = models.CharField(max_length=50, blank=True)
    source_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']


class Challenge(TimeStampedModel):
    company = models.ForeignKey('tenants.Company', on_delete=models.CASCADE, null=True, blank=True, related_name='challenges')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    xp_reward = models.PositiveIntegerField(default=0)
    badge_reward = models.ForeignKey(Badge, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    criteria = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.title


class ChallengeParticipation(TimeStampedModel):
    STATUS_JOINED = 'joined'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES = [(STATUS_JOINED, 'Inscrit'), (STATUS_COMPLETED, 'Terminé')]

    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='participations')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='challenge_participations')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_JOINED)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('challenge', 'user')


class UserStreak(TimeStampedModel):
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='streak')
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_active_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f'{self.user} – {self.current_streak}j'
