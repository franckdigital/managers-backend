from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import EmployeeImportBatch, PermissionCode, RoleDefinition, RolePermission, User, UserDevice
from apps.accounts.services import register_device
from apps.core.constants import Roles


class UserDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDevice
        fields = ('id', 'device_id', 'ip_address', 'user_agent', 'is_active', 'last_seen', 'created_at')


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True, default=None)
    company_subscription_status = serializers.CharField(source='company.subscription_status', read_only=True, default=None)
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True, default=None)
    has_subsidiaries = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'full_name', 'role', 'company', 'company_name',
            'company_subscription_status', 'has_subsidiaries', 'department', 'service', 'team', 'manager', 'manager_name', 'phone', 'avatar',
            'employee_id', 'job_title', 'hire_date', 'birth_date', 'country', 'bio', 'is_trainer_approved',
            'is_active', 'date_joined', 'last_active_at', 'payout_method', 'bank_account_name', 'bank_iban',
        )
        read_only_fields = ('date_joined', 'last_active_at')

    def get_has_subsidiaries(self, obj):
        return obj.company.subsidiaries.exists() if obj.company_id else False


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = (
            'id', 'email', 'password', 'first_name', 'last_name', 'role', 'company', 'department', 'service',
            'team', 'manager', 'phone', 'employee_id', 'job_title', 'hire_date',
        )

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class RegisterSerializer(serializers.ModelSerializer):
    """Public B2C self-registration — always creates a 'student' with no company."""

    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'first_name', 'last_name', 'phone', 'country')

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(role=Roles.STUDENT, **validated_data)
        user.set_password(password)
        user.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Mot de passe actuel incorrect.')
        return value


class BecomeTrainerSerializer(serializers.Serializer):
    bio = serializers.CharField(required=False, allow_blank=True)

    def save(self, **kwargs):
        user = self.context['request'].user
        user.role = Roles.TRAINER if user.role == Roles.STUDENT else user.role
        user.is_trainer_approved = False
        if 'bio' in self.validated_data:
            user.bio = self.validated_data['bio']
        user.save(update_fields=['role', 'is_trainer_approved', 'bio'])
        return user


class EmployeeImportBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeImportBatch
        fields = '__all__'
        read_only_fields = ('company', 'uploaded_by', 'status', 'total_rows', 'success_count', 'error_count', 'errors')


class PermissionCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PermissionCode
        fields = ['id', 'code', 'label', 'category']


class RolePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolePermission
        fields = ['id', 'role', 'permission']
        validators = []  # unique_together handled via get_or_create in the ViewSet


class RoleDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleDefinition
        fields = ['id', 'key', 'label', 'color', 'is_system']
        read_only_fields = ['is_system']


class LmsTokenObtainPairSerializer(TokenObtainPairSerializer):
    device_id = serializers.CharField(required=False, allow_blank=True)
    mfa_code = serializers.CharField(required=False, allow_blank=True)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['company_id'] = user.company_id
        token['full_name'] = user.get_full_name()
        return token

    def validate(self, attrs):
        import pyotp

        device_id = attrs.pop('device_id', '')
        mfa_code = attrs.pop('mfa_code', '')
        data = super().validate(attrs)

        if self.user.mfa_enabled:
            if not mfa_code:
                raise serializers.ValidationError({'mfa_code': 'Code MFA requis.'})
            if not pyotp.TOTP(self.user.mfa_secret).verify(mfa_code, valid_window=1):
                raise serializers.ValidationError({'mfa_code': 'Code MFA invalide.'})

        request = self.context.get('request')
        register_device(self.user, device_id, request, data['refresh'])

        from apps.gamification.services import record_daily_activity
        record_daily_activity(self.user)

        data['user'] = UserSerializer(self.user).data
        return data


class MFASetupSerializer(serializers.Serializer):
    def save(self, **kwargs):
        import pyotp

        user = self.context['request'].user
        secret = pyotp.random_base32()
        user.mfa_secret = secret
        user.save(update_fields=['mfa_secret'])
        totp = pyotp.TOTP(secret)
        return {'secret': secret, 'provisioning_uri': totp.provisioning_uri(name=user.email, issuer_name='LMS PRO')}


class MFACodeSerializer(serializers.Serializer):
    code = serializers.CharField()


class MFADisableSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)

    def validate_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Mot de passe incorrect.')
        return value
