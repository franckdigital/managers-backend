from rest_framework import serializers

from apps.kpi_pro.catalog import RATABLE_TRAINER_KPIS
from apps.kpi_pro.models import TrainerRating

_RATABLE_KEYS = {key for key, _label in RATABLE_TRAINER_KPIS}


class TrainerRatingSerializer(serializers.ModelSerializer):
    trainer_name = serializers.CharField(source='trainer.get_full_name', read_only=True)
    evaluator_name = serializers.CharField(source='evaluator.get_full_name', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True, default=None)
    average_score = serializers.FloatField(read_only=True)

    class Meta:
        model = TrainerRating
        fields = [
            'id', 'evaluator', 'evaluator_name', 'trainer', 'trainer_name',
            'course', 'course_title', 'scores', 'comment', 'average_score', 'created_at',
        ]
        read_only_fields = ('evaluator',)

    def validate_scores(self, value):
        if not isinstance(value, dict) or not value:
            raise serializers.ValidationError("Merci de noter au moins un critère.")
        cleaned = {}
        for key, note in value.items():
            if key not in _RATABLE_KEYS:
                continue
            try:
                note = int(note)
            except (TypeError, ValueError):
                continue
            if 1 <= note <= 5:
                cleaned[key] = note
        if not cleaned:
            raise serializers.ValidationError("Aucune note valide (1 à 5) parmi les critères reconnus.")
        return cleaned
