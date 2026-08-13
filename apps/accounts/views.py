import csv
import io
import secrets

from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.accounts.models import EmployeeImportBatch, PermissionCode, RoleDefinition, RolePermission, User, UserDevice
from apps.accounts.serializers import (
    BecomeTrainerSerializer,
    ChangePasswordSerializer,
    EmployeeImportBatchSerializer,
    LmsTokenObtainPairSerializer,
    MFACodeSerializer,
    MFADisableSerializer,
    MFASetupSerializer,
    PermissionCodeSerializer,
    RegisterSerializer,
    RoleDefinitionSerializer,
    RolePermissionSerializer,
    UserCreateSerializer,
    UserDeviceSerializer,
    UserSerializer,
)
from apps.accounts.services import blacklist_jti
from apps.core.constants import Roles
from apps.core.mixins import AuditLogMixin, CompanyScopedViewSetMixin
from apps.core.permissions import HasRole, IsCompanyAdmin, IsHR, IsSuperAdmin


class LmsTokenObtainPairView(TokenObtainPairView):
    serializer_class = LmsTokenObtainPairSerializer
    permission_classes = [AllowAny]


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get('refresh')
        device_id = request.data.get('device_id')
        if refresh:
            try:
                jti = RefreshToken(refresh)['jti']
                blacklist_jti(jti)
            except Exception:
                pass
        if device_id:
            request.user.devices.filter(device_id=device_id).update(is_active=False)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.GenericAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=['password'])
        return Response({'detail': 'Mot de passe mis à jour.'})


class MFASetupView(generics.GenericAPIView):
    """Step 1: generates a TOTP secret and provisioning URI (for a QR code), but does
    not enable MFA yet — that only happens once the user proves possession via /mfa/verify/."""

    serializer_class = MFASetupSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data={})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save())


class MFAVerifyView(generics.GenericAPIView):
    serializer_class = MFACodeSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import pyotp

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.mfa_secret:
            return Response({'detail': "Aucune configuration MFA en attente. Appelez /mfa/setup/ au préalable."}, status=400)
        if not pyotp.TOTP(user.mfa_secret).verify(serializer.validated_data['code'], valid_window=1):
            return Response({'detail': 'Code invalide.'}, status=400)

        user.mfa_enabled = True
        user.save(update_fields=['mfa_enabled'])
        return Response({'detail': 'MFA activé.'})


class MFADisableView(generics.GenericAPIView):
    serializer_class = MFADisableSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.mfa_enabled = False
        user.mfa_secret = ''
        user.save(update_fields=['mfa_enabled', 'mfa_secret'])
        return Response({'detail': 'MFA désactivé.'})


class BecomeTrainerView(generics.GenericAPIView):
    serializer_class = BecomeTrainerSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data)


class UserViewSet(AuditLogMixin, CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = User.objects.select_related('company', 'department', 'service', 'team', 'manager').all()
    permission_classes = [IsHR]
    filterset_fields = ['role', 'department', 'service', 'team', 'manager', 'is_active']
    search_fields = ['email', 'first_name', 'last_name', 'employee_id']

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ('suspend', 'activate'):
            return [HasRole.for_roles(Roles.TRAINING_CENTER_ADMIN)()]
        return super().get_permissions()

    def get_queryset(self):
        from django.db.models import Q

        user = self.request.user
        company_isnull = self.request.query_params.get('company__isnull')

        if (user.is_authenticated and
                getattr(user, 'role', None) == Roles.TRAINING_CENTER_ADMIN):
            base = User.objects.select_related('company', 'department', 'service', 'team', 'manager')
            if company_isnull is not None and company_isnull.lower() == 'true':
                # B2C learners list — bypass company scope
                return base.filter(company__isnull=True, role=Roles.STUDENT)
            # Default: own company users + B2C students (latter needed for object-level suspend/activate)
            return base.filter(Q(company_id=user.company_id) | Q(company__isnull=True, role=Roles.STUDENT))

        qs = super().get_queryset()
        if company_isnull is not None:
            qs = qs.filter(company__isnull=company_isnull.lower() == 'true')
        return qs

    @action(detail=True, methods=['get'])
    def direct_reports(self, request, pk=None):
        user = self.get_object()
        reports = User.objects.filter(manager=user)
        return Response(UserSerializer(reports, many=True).data)

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=['is_active'])
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=['is_active'])
        return Response(UserSerializer(user).data)


class EmployeeImportBatchViewSet(viewsets.ModelViewSet):
    queryset = EmployeeImportBatch.objects.select_related('company', 'uploaded_by').all()
    serializer_class = EmployeeImportBatchSerializer
    permission_classes = [IsCompanyAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_superuser or user.role == Roles.SUPER_ADMIN:
            return qs
        return qs.filter(company_id=user.company_id)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, uploaded_by=self.request.user)

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        batch = self.get_object()
        decoded = batch.file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded))

        success, errors = 0, []
        rows = list(reader)
        for i, row in enumerate(rows, start=1):
            try:
                email = row['email'].strip()
                if User.objects.filter(email=email).exists():
                    raise ValueError('Email déjà utilisé')
                User.objects.create_user(
                    email=email,
                    password=secrets.token_urlsafe(12),
                    first_name=row.get('first_name', '').strip(),
                    last_name=row.get('last_name', '').strip(),
                    role=row.get('role', Roles.EMPLOYEE).strip() or Roles.EMPLOYEE,
                    employee_id=row.get('employee_id', '').strip(),
                    job_title=row.get('job_title', '').strip(),
                    company=batch.company,
                )
                success += 1
            except Exception as exc:
                errors.append({'row': i, 'email': row.get('email'), 'error': str(exc)})

        batch.total_rows = len(rows)
        batch.success_count = success
        batch.error_count = len(errors)
        batch.errors = errors
        batch.status = EmployeeImportBatch.STATUS_FAILED if errors and success == 0 else EmployeeImportBatch.STATUS_DONE
        batch.save()
        return Response(EmployeeImportBatchSerializer(batch).data)


class UserDeviceViewSet(viewsets.ReadOnlyModelViewSet):
    """§25.4 — lets a learner see and revoke their own active sessions/devices, and lets
    HR/company admins kill a compromised employee's sessions on demand."""

    serializer_class = UserDeviceSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        qs = UserDevice.objects.select_related('user')
        if user.is_superuser or user.role in (Roles.SUPER_ADMIN, Roles.HR, Roles.COMPANY_ADMIN):
            return qs
        return qs.filter(user=user)

    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        device = self.get_object()
        device.is_active = False
        device.save(update_fields=['is_active'])
        if device.refresh_token_jti:
            blacklist_jti(device.refresh_token_jti)

        from apps.notifications.services import notify_user

        notify_user(
            device.user,
            'Appareil révoqué',
            f"L'accès depuis l'appareil « {device.user_agent or device.device_id} » a été révoqué.",
            data={'device_id': device.device_id},
        )
        return Response(UserDeviceSerializer(device).data)

    @action(detail=False, methods=['post'], url_path='revoke-others')
    def revoke_others(self, request):
        current_device_id = request.META.get('HTTP_X_DEVICE_ID')
        others = list(UserDevice.objects.filter(user=request.user, is_active=True).exclude(device_id=current_device_id))
        for device in others:
            device.is_active = False
            device.save(update_fields=['is_active'])
            if device.refresh_token_jti:
                blacklist_jti(device.refresh_token_jti)
        return Response({'revoked': len(others)})


class PermissionCodeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PermissionCode.objects.all().order_by('category', 'code')
    serializer_class = PermissionCodeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # always return all permissions (bounded set)


class RolePermissionViewSet(viewsets.ModelViewSet):
    queryset = RolePermission.objects.select_related('permission').all()
    serializer_class = RolePermissionSerializer
    permission_classes = [IsSuperAdmin]
    filterset_fields = ['role']
    http_method_names = ['get', 'post', 'delete', 'head', 'options']
    pagination_class = None  # matrix needs the complete set

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from django.db import IntegrityError
        try:
            obj, created = RolePermission.objects.get_or_create(
                role=serializer.validated_data['role'],
                permission=serializer.validated_data['permission'],
            )
        except IntegrityError:
            # race condition on parallel toggleAll — fetch the existing record
            obj = RolePermission.objects.get(
                role=serializer.validated_data['role'],
                permission=serializer.validated_data['permission'],
            )
            created = False
        return Response(
            RolePermissionSerializer(obj).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class RoleDefinitionViewSet(viewsets.ModelViewSet):
    queryset = RoleDefinition.objects.all()
    serializer_class = RoleDefinitionSerializer
    pagination_class = None  # roles are a small bounded set

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsSuperAdmin()]

    def perform_destroy(self, instance):
        from rest_framework.exceptions import ValidationError
        if instance.is_system:
            raise ValidationError("Les rôles système ne peuvent pas être supprimés.")
        instance.delete()
