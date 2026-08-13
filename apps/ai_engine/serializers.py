from rest_framework import serializers

from apps.ai_engine.models import AIConversation, AIGeneratedQuiz, AIMessage, CourseRecommendation, DifficultyAlert


class AIMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIMessage
        fields = '__all__'
        read_only_fields = ('conversation',)


class AIConversationSerializer(serializers.ModelSerializer):
    messages = AIMessageSerializer(many=True, read_only=True)

    class Meta:
        model = AIConversation
        fields = '__all__'
        read_only_fields = ('user',)


class ChatRequestSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField(required=False, allow_null=True)
    course_id = serializers.IntegerField(required=False, allow_null=True)
    message = serializers.CharField()


class SummarizeRequestSerializer(serializers.Serializer):
    text = serializers.CharField()


class GenerateQuizRequestSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()
    chapter_id = serializers.IntegerField(required=False, allow_null=True)
    content = serializers.CharField()
    num_questions = serializers.IntegerField(default=5, min_value=1, max_value=20)


class TranslateRequestSerializer(serializers.Serializer):
    text = serializers.CharField()
    target_lang = serializers.CharField()


class AIGeneratedQuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIGeneratedQuiz
        fields = '__all__'
        read_only_fields = ('created_by',)


class CourseRecommendationSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = CourseRecommendation
        fields = '__all__'


class DifficultyAlertSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = DifficultyAlert
        fields = '__all__'
