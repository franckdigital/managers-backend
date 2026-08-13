from rest_framework import serializers

from apps.assessments.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentQuestion,
    AssignmentSubmission,
    AttemptAnswer,
    Question,
    QuestionBank,
    QuestionChoice,
)


class QuestionChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionChoice
        fields = '__all__'


class QuestionChoicePublicSerializer(serializers.ModelSerializer):
    """Hides is_correct from learners while an attempt is in progress."""

    class Meta:
        model = QuestionChoice
        fields = ('id', 'text', 'order')


class QuestionSerializer(serializers.ModelSerializer):
    choices = QuestionChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = '__all__'


class QuestionPublicSerializer(serializers.ModelSerializer):
    choices = QuestionChoicePublicSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ('id', 'text', 'question_type', 'is_multiple_answer', 'points', 'choices', 'metadata')


class QuestionBankSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    questions_count = serializers.IntegerField(source='questions.count', read_only=True)

    class Meta:
        model = QuestionBank
        fields = '__all__'
        read_only_fields = ('created_by',)


class AssessmentQuestionSerializer(serializers.ModelSerializer):
    question_text       = serializers.CharField(source='question.text', read_only=True)
    question_type       = serializers.CharField(source='question.question_type', read_only=True)
    difficulty          = serializers.CharField(source='question.difficulty', read_only=True)
    points              = serializers.FloatField(source='question.points', read_only=True)

    class Meta:
        model = AssessmentQuestion
        fields = '__all__'


class AssessmentSerializer(serializers.ModelSerializer):
    questions_count = serializers.SerializerMethodField()
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = Assessment
        fields = '__all__'

    def get_questions_count(self, obj):
        if obj.is_randomized and obj.question_bank_id:
            if obj.question_pool_size:
                return obj.question_pool_size
            return obj.question_bank.questions.count()
        return obj.assessment_questions.count()


class ProctoringEventSerializer(serializers.Serializer):
    event_type = serializers.CharField()
    details = serializers.DictField(required=False, default=dict)


class AttemptAnswerSubmitSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_choice_ids = serializers.ListField(child=serializers.IntegerField(), required=False, default=list)
    text_answer = serializers.CharField(required=False, allow_blank=True, default='')
    matching_answer = serializers.DictField(required=False, default=dict)


class AttemptAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttemptAnswer
        fields = '__all__'
        read_only_fields = ('is_correct', 'points_awarded')


class AssessmentAttemptSerializer(serializers.ModelSerializer):
    answers = AttemptAnswerSerializer(many=True, read_only=True)
    assessment_title = serializers.CharField(source='assessment.title', read_only=True)

    class Meta:
        model = AssessmentAttempt
        fields = '__all__'
        read_only_fields = ('user', 'attempt_number', 'score', 'is_passed', 'status', 'questions_snapshot', 'submitted_at')


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssignmentSubmission
        fields = '__all__'
        read_only_fields = ('grade', 'feedback', 'graded_by', 'graded_at')


class GradeAssignmentSerializer(serializers.Serializer):
    grade = serializers.DecimalField(max_digits=5, decimal_places=2)
    feedback = serializers.CharField(required=False, allow_blank=True)
