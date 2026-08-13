from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import EmployeeImportBatch, PermissionCode, RolePermission, User, UserDevice


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ('email',)
    list_display = ('email', 'first_name', 'last_name', 'role', 'company', 'is_active', 'is_staff')
    list_filter = ('role', 'company', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name', 'employee_id')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Profil', {'fields': (
            'first_name', 'last_name', 'phone', 'avatar', 'bio', 'birth_date', 'country',
        )}),
        ('Organisation', {'fields': (
            'role', 'company', 'department', 'service', 'team', 'manager', 'employee_id', 'job_title', 'hire_date',
        )}),
        ('Permissions', {'fields': (
            'is_active', 'is_staff', 'is_superuser', 'is_trainer_approved', 'mfa_enabled',
            'groups', 'user_permissions',
        )}),
        ('Dates', {'fields': ('last_login', 'date_joined', 'last_active_at')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'password1', 'password2', 'role')}),
    )


@admin.register(PermissionCode)
class PermissionCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'label', 'category')


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ('role', 'permission')
    list_filter = ('role',)


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_id', 'ip_address', 'is_active', 'last_seen')
    list_filter = ('is_active',)


@admin.register(EmployeeImportBatch)
class EmployeeImportBatchAdmin(admin.ModelAdmin):
    list_display = ('company', 'status', 'total_rows', 'success_count', 'error_count', 'created_at')
    list_filter = ('status',)
