from django.contrib import admin

from apps.tenants.models import Company, CompanySubscription, Department, Service, SubscriptionPlan, Team


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'price', 'billing_cycle', 'max_users', 'is_active')
    search_fields = ('name', 'code')


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'sector', 'country', 'subscription_status', 'plan', 'is_active')
    search_fields = ('name', 'slug', 'email')
    list_filter = ('subscription_status', 'is_active')


@admin.register(CompanySubscription)
class CompanySubscriptionAdmin(admin.ModelAdmin):
    list_display = ('company', 'plan', 'status', 'start_date', 'end_date', 'auto_renew')
    list_filter = ('status',)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'code')


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'company')


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'service', 'company', 'manager')
