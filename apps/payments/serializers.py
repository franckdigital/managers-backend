from rest_framework import serializers

from apps.payments.models import Invoice, Order, OrderItem, Payment, Payout, PayoutItem


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'


class PayoutItemSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='order_item.title_snapshot', read_only=True)

    class Meta:
        model = PayoutItem
        fields = '__all__'


class PayoutSerializer(serializers.ModelSerializer):
    trainer_name = serializers.CharField(source='trainer.get_full_name', read_only=True)
    items = PayoutItemSerializer(many=True, read_only=True)

    class Meta:
        model = Payout
        fields = '__all__'
        read_only_fields = (
            'trainer', 'gross_amount', 'commission_rate', 'commission_amount', 'net_amount',
            'status', 'processed_by', 'processed_at',
        )


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ('raw_response',)


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    invoice = InvoiceSerializer(read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    subscription_plan_name = serializers.CharField(source='subscription_plan.name', read_only=True)

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ('user', 'company', 'status', 'subtotal', 'discount_amount', 'total_amount', 'paid_at')


class CheckoutSerializer(serializers.Serializer):
    coupon_code = serializers.CharField(required=False, allow_blank=True)
    provider = serializers.ChoiceField(choices=['manual', 'cash', 'stripe', 'cinetpay', 'paypal'])
