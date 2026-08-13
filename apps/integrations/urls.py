from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.integrations.views import (
    APIClientViewSet,
    ERPConnectorViewSet,
    SSOConfigurationViewSet,
    SSOLoginCallbackView,
    SSOLoginStartView,
    WebhookEndpointViewSet,
)

router = DefaultRouter()
router.register('api-clients', APIClientViewSet, basename='api-client')
router.register('webhooks', WebhookEndpointViewSet, basename='webhook-endpoint')
router.register('erp-connectors', ERPConnectorViewSet, basename='erp-connector')
router.register('sso-configurations', SSOConfigurationViewSet, basename='sso-configuration')

urlpatterns = [
    path('sso/login/<slug:company_slug>/', SSOLoginStartView.as_view(), name='sso-login-start'),
    path('sso/callback/', SSOLoginCallbackView.as_view(), name='sso-login-callback'),
] + router.urls
