from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.payments.views import (
    CheckoutView,
    CinetPayWebhookView,
    OrderViewSet,
    PayoutViewSet,
    PayPalWebhookView,
    StripeWebhookView,
)

router = DefaultRouter()
router.register('orders', OrderViewSet, basename='order')
router.register('payouts', PayoutViewSet, basename='payout')

urlpatterns = [
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('webhooks/cinetpay/', CinetPayWebhookView.as_view(), name='cinetpay-webhook'),
    path('webhooks/stripe/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('webhooks/paypal/', PayPalWebhookView.as_view(), name='paypal-webhook'),
] + router.urls
