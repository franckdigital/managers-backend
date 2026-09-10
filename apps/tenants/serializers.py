from rest_framework import serializers

from apps.tenants.models import (
    Company, CompanySubscription, Department, Service, SubscriptionPlan,
    Team, TeamSubscription, UserSubscription,
)


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = '__all__'


class UserSubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    billing_cycle = serializers.CharField(source='plan.billing_cycle', read_only=True)
    currency = serializers.CharField(source='plan.currency', read_only=True)
    is_global = serializers.BooleanField(source='plan.is_global', read_only=True)
    included_course_titles = serializers.SerializerMethodField()

    def get_included_course_titles(self, obj):
        if obj.plan.is_global:
            return []
        return list(obj.plan.included_courses.values_list('title', flat=True))

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
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    billing_cycle = serializers.CharField(source='plan.billing_cycle', read_only=True)
    is_global = serializers.BooleanField(source='plan.is_global', read_only=True)

    class Meta:
        model = CompanySubscription
        fields = '__all__'


class CompanyScopedWriteMixin:
    """`company` is writable but optional at field level: a non-super user may omit it
    (the viewset's CompanyScopedViewSetMixin fills it from their own company) or target a
    company in their tree; a super admin *must* provide one (enforced in `validate`)."""

    company = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(), required=False, allow_null=True,
    )

    def _request_user(self):
        request = self.context.get('request')
        return getattr(request, 'user', None)

    def _is_platform_admin(self, user):
        return bool(user) and user.is_authenticated and (
            user.is_superuser or getattr(user, 'role', None) == 'super_admin'
        )

    def validate_company(self, value):
        user = self._request_user()
        if self._is_platform_admin(user):
            return value
        if user is None or not user.is_authenticated:
            return value
        company = getattr(user, 'company', None)
        if company is None:
            raise serializers.ValidationError("Vous n'êtes rattaché à aucune entreprise.")
        if value is not None and value.id not in company.get_descendant_ids():
            raise serializers.ValidationError("Cette entreprise est hors de votre périmètre.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        user = self._request_user()
        # A super admin has no company of their own, so `company` cannot be auto-filled —
        # they must pick one when creating a department / service / team.
        if self.instance is None and attrs.get('company') is None:
            if self._is_platform_admin(user):
                raise serializers.ValidationError({'company': "L'entreprise est requise."})
        return attrs


class DepartmentSerializer(CompanyScopedWriteMixin, serializers.ModelSerializer):
    users_count = serializers.IntegerField(source='members.count', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = Department
        fields = '__all__'


class ServiceSerializer(CompanyScopedWriteMixin, serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = Service
        fields = '__all__'

    def validate(self, attrs):
        attrs = super().validate(attrs)
        dept = attrs.get('department') or getattr(self.instance, 'department', None)
        company = attrs.get('company') or getattr(self.instance, 'company', None)
        if dept and company and dept.company_id != company.id:
            raise serializers.ValidationError({'department': "Ce département n'appartient pas à l'entreprise choisie."})
        return attrs


class TeamSerializer(CompanyScopedWriteMixin, serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)
    members_count = serializers.IntegerField(source='members.count', read_only=True)

    class Meta:
        model = Team
        fields = '__all__'
        read_only_fields = ('plan', 'subscription_status', 'subscription_start', 'subscription_end')

    def validate(self, attrs):
        attrs = super().validate(attrs)
        service = attrs.get('service') or getattr(self.instance, 'service', None)
        company = attrs.get('company') or getattr(self.instance, 'company', None)
        if service and company and service.company_id != company.id:
            raise serializers.ValidationError({'service': "Ce service n'appartient pas à l'entreprise choisie."})
        manager = attrs.get('manager') or getattr(self.instance, 'manager', None)
        if manager and company and manager.company_id and manager.company_id != company.id:
            raise serializers.ValidationError({'manager': "Ce manager n'appartient pas à l'entreprise choisie."})
        return attrs


class TeamSubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)
    billing_cycle = serializers.CharField(source='plan.billing_cycle', read_only=True)
    is_global = serializers.BooleanField(source='plan.is_global', read_only=True)

    class Meta:
        model = TeamSubscription
        fields = '__all__'
