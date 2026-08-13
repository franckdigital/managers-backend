from rest_framework import serializers

from apps.hr_analytics.models import (
    CourseSkill,
    EmployeeSkill,
    Evaluation360Campaign,
    Evaluation360Response,
    IndividualDevelopmentPlan,
    JobRole,
    JobRoleSkillRequirement,
    PDIObjective,
    Skill,
    TrainingBudgetEntry,
)


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = '__all__'


class CourseSkillSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source='skill.name', read_only=True)

    class Meta:
        model = CourseSkill
        fields = '__all__'


class JobRoleSkillRequirementSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source='skill.name', read_only=True)

    class Meta:
        model = JobRoleSkillRequirement
        fields = '__all__'


class JobRoleSerializer(serializers.ModelSerializer):
    skill_requirements = JobRoleSkillRequirementSerializer(many=True, read_only=True)

    class Meta:
        model = JobRole
        fields = '__all__'


class EmployeeSkillSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source='skill.name', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = EmployeeSkill
        fields = '__all__'


class PDIObjectiveSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source='skill.name', read_only=True, default=None)
    course_title = serializers.CharField(source='course.title', read_only=True, default=None)

    class Meta:
        model = PDIObjective
        fields = '__all__'


class IndividualDevelopmentPlanSerializer(serializers.ModelSerializer):
    objectives = PDIObjectiveSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = IndividualDevelopmentPlan
        fields = '__all__'
        read_only_fields = ('created_by',)


class Evaluation360ResponseSerializer(serializers.ModelSerializer):
    evaluator_name = serializers.CharField(source='evaluator.get_full_name', read_only=True)

    class Meta:
        model = Evaluation360Response
        fields = '__all__'
        read_only_fields = ('evaluator',)


class Evaluation360CampaignSerializer(serializers.ModelSerializer):
    responses = Evaluation360ResponseSerializer(many=True, read_only=True)
    target_user_name = serializers.CharField(source='target_user.get_full_name', read_only=True)

    class Meta:
        model = Evaluation360Campaign
        fields = '__all__'
        read_only_fields = ('created_by', 'company')


class TrainingBudgetEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingBudgetEntry
        fields = '__all__'
        read_only_fields = ('company',)
