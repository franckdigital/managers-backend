from rest_framework import serializers

from apps.learning_paths.models import (
    LearningPath,
    LearningPathEnrollment,
    LearningPathStep,
    SessionParticipant,
    TrainingSession,
)


class LearningPathStepSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = LearningPathStep
        fields = '__all__'


class LearningPathSerializer(serializers.ModelSerializer):
    steps = LearningPathStepSerializer(many=True, read_only=True)

    class Meta:
        model = LearningPath
        fields = '__all__'
        read_only_fields = ('created_by',)


class LearningPathEnrollmentSerializer(serializers.ModelSerializer):
    path_title = serializers.CharField(source='path.title', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = LearningPathEnrollment
        fields = '__all__'
        read_only_fields = ('progress_percent', 'status', 'started_at', 'completed_at')


class SessionParticipantSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = SessionParticipant
        fields = '__all__'


class TrainingSessionSerializer(serializers.ModelSerializer):
    participants = SessionParticipantSerializer(many=True, read_only=True)
    trainer_name = serializers.CharField(source='trainer.get_full_name', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = TrainingSession
        fields = '__all__'
