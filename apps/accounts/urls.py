from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from apps.accounts.views import (
    BecomeTrainerView,
    ChangePasswordView,
    EmployeeImportBatchViewSet,
    LmsTokenObtainPairView,
    LogoutView,
    MeView,
    MFADisableView,
    MFASetupView,
    MFAVerifyView,
    PermissionCodeViewSet,
    RegisterView,
    RoleDefinitionViewSet,
    RolePermissionViewSet,
    UserDeviceViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register('users', UserViewSet, basename='user')
router.register('employee-imports', EmployeeImportBatchViewSet, basename='employee-import')
router.register('devices', UserDeviceViewSet, basename='user-device')
router.register('permissions', PermissionCodeViewSet, basename='permission')
router.register('role-permissions', RolePermissionViewSet, basename='role-permission')
router.register('role-definitions', RoleDefinitionViewSet, basename='role-definition')

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LmsTokenObtainPairView.as_view(), name='auth-login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='auth-refresh'),
    path('auth/verify/', TokenVerifyView.as_view(), name='auth-verify'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('auth/me/', MeView.as_view(), name='auth-me'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
    path('auth/become-trainer/', BecomeTrainerView.as_view(), name='auth-become-trainer'),
    path('auth/mfa/setup/', MFASetupView.as_view(), name='auth-mfa-setup'),
    path('auth/mfa/verify/', MFAVerifyView.as_view(), name='auth-mfa-verify'),
    path('auth/mfa/disable/', MFADisableView.as_view(), name='auth-mfa-disable'),
] + router.urls
