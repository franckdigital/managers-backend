from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Cart, Coupon
from apps.core.constants import Roles
from apps.core.permissions import HasRole
from apps.payments.models import Order, Payout
from apps.payments.providers import get_provider
from apps.payments.serializers import CheckoutSerializer, OrderSerializer, PayoutSerializer
from apps.payments.services import (
    approve_payout,
    create_order_from_cart,
    initiate_payment,
    mark_order_paid,
    mark_payout_paid,
    reject_payout,
    request_payout,
    trainer_unpaid_earnings,
)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'order_type']

    def get_queryset(self):
        user = self.request.user
        qs = Order.objects.select_related('coupon', 'subscription_plan').prefetch_related('items', 'payments', 'invoice')
        if user.is_superuser or user.role == 'super_admin':
            return qs
        if user.role in ('company_admin', 'hr') and user.company_id:
            return qs.filter(company_id=user.company_id)
        return qs.filter(user=user)

    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        """Admin validates a pending cash payment, optionally uploading a receipt."""
        from apps.payments.models import Payment as PaymentModel

        user = request.user
        if not (user.is_superuser or user.role in ('super_admin', 'company_admin')):
            return Response({'detail': 'Accès refusé.'}, status=403)

        order = self.get_object()
        if order.status == Order.STATUS_PAID:
            return Response({'detail': 'Cette commande est déjà payée.'}, status=400)

        provider = request.data.get('provider', PaymentModel.PROVIDER_CASH)
        payment, _ = PaymentModel.objects.get_or_create(
            order=order, provider=provider,
            defaults={'amount': order.total_amount, 'currency': order.currency},
        )
        receipt = request.FILES.get('receipt')
        if receipt:
            payment.receipt = receipt
        payment.status = PaymentModel.STATUS_SUCCEEDED
        payment.save()

        mark_order_paid(order)
        order.refresh_from_db()
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=['post'], url_path='mock-paid')
    def mock_paid(self, request, pk=None):
        """Simulates a successful CinetPay payment — only active when CINETPAY_MOCK=True."""
        from django.conf import settings
        if not getattr(settings, 'CINETPAY_MOCK', False):
            return Response(status=404)
        order = self.get_object()
        if order.user != request.user:
            return Response({'detail': 'Accès refusé.'}, status=403)
        if order.status == Order.STATUS_PAID:
            return Response(OrderSerializer(order).data)
        mark_order_paid(order)
        order.refresh_from_db()
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Admin rejects/cancels a pending order (e.g. cash proof not valid)."""
        user = request.user
        if not (user.is_superuser or user.role in ('super_admin', 'company_admin')):
            return Response({'detail': 'Accès refusé.'}, status=403)

        order = self.get_object()
        if order.status != Order.STATUS_PENDING:
            return Response({'detail': 'Seules les commandes en attente peuvent être annulées.'}, status=400)

        order.status = Order.STATUS_FAILED
        order.save(update_fields=['status'])

        from apps.notifications.services import notify_user
        notify_user(
            order.user,
            'Paiement non validé',
            f"Votre demande d'abonnement #{order.id} n'a pas pu être validée. Contactez le support.",
            data={'order_id': order.id},
        )
        return Response(OrderSerializer(order).data)


class PayoutViewSet(viewsets.ModelViewSet):
    serializer_class = PayoutSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'trainer']
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        qs = Payout.objects.select_related('trainer').prefetch_related('items')
        if user.is_superuser or user.role == Roles.SUPER_ADMIN:
            return qs
        if user.role == Roles.COMPANY_ADMIN and user.company_id:
            return qs.filter(trainer__company_id=user.company_id)
        return qs.filter(trainer=user)

    def create(self, request, *args, **kwargs):
        if request.user.role != Roles.TRAINER:
            return Response({'detail': 'Seuls les formateurs peuvent demander un paiement.'}, status=403)
        try:
            payout = request_payout(request.user)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=400)
        return Response(PayoutSerializer(payout).data, status=201)

    @action(detail=False, methods=['get'], url_path='unpaid-earnings')
    def unpaid_earnings(self, request):
        if request.user.role != Roles.TRAINER:
            return Response({'detail': 'Réservé aux formateurs.'}, status=403)
        items = trainer_unpaid_earnings(request.user)
        total = sum((item.unit_price for item in items), start=0)
        return Response({'pending_items': items.count(), 'gross_amount': str(total)})

    @action(detail=True, methods=['post'], permission_classes=[HasRole.for_roles(Roles.SUPER_ADMIN, Roles.COMPANY_ADMIN)])
    def approve(self, request, pk=None):
        payout = self.get_object()
        return Response(PayoutSerializer(approve_payout(payout, request.user)).data)

    @action(detail=True, methods=['post'], url_path='mark-paid', permission_classes=[HasRole.for_roles(Roles.SUPER_ADMIN, Roles.COMPANY_ADMIN)])
    def mark_paid(self, request, pk=None):
        payout = self.get_object()
        return Response(PayoutSerializer(mark_payout_paid(payout, request.user)).data)

    @action(detail=True, methods=['post'], permission_classes=[HasRole.for_roles(Roles.SUPER_ADMIN, Roles.COMPANY_ADMIN)])
    def reject(self, request, pk=None):
        payout = self.get_object()
        return Response(PayoutSerializer(reject_payout(payout, request.user, request.data.get('notes', ''))).data)


class CheckoutView(generics.GenericAPIView):
    serializer_class = CheckoutSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = None  # accept JSON and multipart (for cash proof upload)

    def get_parsers(self):
        from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
        return [MultiPartParser(), FormParser(), JSONParser()]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart, _ = Cart.objects.get_or_create(user=request.user)
        coupon = None
        code = serializer.validated_data.get('coupon_code')
        if code:
            coupon = Coupon.objects.filter(code=code).first()

        order = create_order_from_cart(request.user, cart, coupon=coupon)
        provider = serializer.validated_data['provider']

        try:
            payment, result = initiate_payment(order, provider)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error('Checkout payment error [%s]: %s', provider, exc, exc_info=True)
            order.delete()
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # Attach cash proof file if provided
        proof = request.FILES.get('payment_proof')
        if proof and provider == 'cash':
            payment.receipt = proof
            payment.save(update_fields=['receipt'])

        if payment.provider == 'manual':
            mark_order_paid(order)
            order.refresh_from_db()

        return Response({
            'order': OrderSerializer(order).data,
            'redirect_url': result.redirect_url,
            'client_secret': result.client_secret,
            'pending_validation': provider == 'cash',
        }, status=status.HTTP_201_CREATED)


class CinetPayWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        transaction_id = request.data.get('cpm_trans_id') or request.data.get('transaction_id')
        if not transaction_id:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        from apps.payments.models import Payment

        payment = Payment.objects.filter(provider_reference=transaction_id, provider='cinetpay').select_related('order').first()
        if not payment:
            return Response(status=status.HTTP_404_NOT_FOUND)

        provider = get_provider('cinetpay')
        result = provider.verify_payment(transaction_id)
        payment.status = Payment.STATUS_SUCCEEDED if result['status'] == 'succeeded' else Payment.STATUS_FAILED
        payment.raw_response = result.get('raw', {})
        payment.save(update_fields=['status', 'raw_response'])

        if payment.status == Payment.STATUS_SUCCEEDED:
            mark_order_paid(payment.order)

        return Response({'detail': 'ok'})


class PayPalWebhookView(APIView):
    """Called when the buyer returns from PayPal approval — captures the order
    server-side rather than trusting any client-supplied status."""

    permission_classes = [AllowAny]

    def post(self, request):
        paypal_order_id = request.data.get('orderID') or request.data.get('order_id')
        if not paypal_order_id:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        from apps.payments.models import Payment

        payment = Payment.objects.filter(provider_reference=paypal_order_id, provider='paypal').select_related('order').first()
        if not payment:
            return Response(status=status.HTTP_404_NOT_FOUND)

        provider = get_provider('paypal')
        result = provider.verify_payment(paypal_order_id)
        payment.status = Payment.STATUS_SUCCEEDED if result['status'] == 'succeeded' else Payment.STATUS_FAILED
        payment.raw_response = result.get('raw', {})
        payment.save(update_fields=['status', 'raw_response'])

        if payment.status == Payment.STATUS_SUCCEEDED:
            mark_order_paid(payment.order)

        return Response({'detail': 'ok'})


class StripeWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        payment_intent_id = request.data.get('data', {}).get('object', {}).get('id')
        if not payment_intent_id:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        from apps.payments.models import Payment

        payment = Payment.objects.filter(provider_reference=payment_intent_id, provider='stripe').select_related('order').first()
        if not payment:
            return Response(status=status.HTTP_404_NOT_FOUND)

        provider = get_provider('stripe')
        result = provider.verify_payment(payment_intent_id)
        payment.status = Payment.STATUS_SUCCEEDED if result['status'] == 'succeeded' else Payment.STATUS_FAILED
        payment.save(update_fields=['status'])

        if payment.status == Payment.STATUS_SUCCEEDED:
            mark_order_paid(payment.order)

        return Response({'detail': 'ok'})
