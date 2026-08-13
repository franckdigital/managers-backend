from rest_framework import serializers

from apps.tenants.models import Company, CompanySubscription, Department, Service, SubscriptionPlan, Team, UserSubscription


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = '__all__'


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    billing_cycle = serializers.CharField(source='plan.billing_cycle', read_only=True)
    currency = serializers.CharField(source='plan.currency', read_only=True)

    class Meta:
        model = UserSubscription
        fields = '__all__'
        read_only_fields = ('user', 'status', 'start_date', 'end_date', 'amount_paid')


class CompanySerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    users_count = serializers.IntegerField(source='users.count', read_only=True)
    departments_count = serializers.IntegerField(source='departments.count', read_only=True)
    subsidiaries_count = serializers.IntegerField(source='subsidiaries.count', read_only=True)
    parent_name = serializers.CharField(source='parent.name', read_only=True)

    class Meta:
        model = Company
        fields = '__all__'
        read_only_fields = ('slug',)


class CompanySubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanySubscription
        fields = '__all__'


class DepartmentSerializer(serializers.ModelSerializer):
    users_count = serializers.IntegerField(source='members.count', read_only=True)

    class Meta:
        model = Department
        fields = '__all__'
        read_only_fields = ('company',)


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__'
        read_only_fields = ('company',)


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = '__all__'
        read_only_fields = ('company',)
