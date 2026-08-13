from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel


class TrainerRating(TimeStampedModel):
    """Notation d'un formateur par un apprenant — alimente en direct les KPI
    Formateurs de perception (satisfaction, animation, préparation…) au lieu
    d'une simple heuristique basée sur les avis de cours."""

    evaluator = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='trainer_ratings_given')
    trainer = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='trainer_ratings_received')
    course = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    scores = models.JSONField(default=dict, blank=True, help_text='{kpi_key: note 1-5}')
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ('evaluator', 'trainer', 'course')
        ordering = ['-created_at']

    def __str__(self):
        return f'Évaluation {self.trainer} par {self.evaluator}'

    @property
    def average_score(self):
        values = [float(v) for v in (self.scores or {}).values() if v is not None]
        return round(sum(values) / len(values), 2) if values else None
