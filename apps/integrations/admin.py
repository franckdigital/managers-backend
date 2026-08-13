from django.contrib import admin

from apps.integrations.models import APIClient, ERPConnector, SSOConfiguration, WebhookDelivery, WebhookEndpoint


@admin.register(APIClient)
class APIClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'api_key', 'is_active')


class WebhookDeliveryInline(admin.TabularInline):
    model = WebhookDelivery
    extra = 0
    readonly_fields = ('event_type', 'response_status', 'success', 'delivered_at')


@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(admin.ModelAdmin):
    list_display = ('url', 'company', 'is_active')
    inlines = [WebhookDeliveryInline]


@admin.register(ERPConnector)
class ERPConnectorAdmin(admin.ModelAdmin):
    list_display = ('company', 'provider', 'is_active', 'last_sync_at', 'last_sync_status')


@admin.register(SSOConfiguration)
class SSOConfigurationAdmin(admin.ModelAdmin):
    list_display = ('company', 'provider', 'is_active')
