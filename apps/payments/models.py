from django.db import models

from apps.core.models import TimeStampedModel


class Order(TimeStampedModel):
    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'
    STATUS_FAILED = 'failed'
    STATUS_REFUNDED = 'refunded'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'En attente'),
        (STATUS_PAID, 'Payée'),
        (STATUS_FAILED, 'Échouée'),
        (STATUS_REFUNDED, 'Remboursée'),
    ]

    TYPE_COURSE_PURCHASE = 'course_purchase'
    TYPE_SUBSCRIPTION = 'subscription'
    TYPE_CHOICES = [(TYPE_COURSE_PURCHASE, 'Achat de formation'), (TYPE_SUBSCRIPTION, 'Abonnement entreprise')]

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='orders')
    company = models.ForeignKey(
        'tenants.Company', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders'
    )
    subscription_plan = models.ForeignKey(
        'tenants.SubscriptionPlan', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders'
    )
    order_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_COURSE_PURCHASE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    coupon = models.ForeignKey('catalog.Coupon', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='XOF')
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Order #{self.id} – {self.user} – {self.status}'


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    course = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, related_name='order_items')
    bundle = models.ForeignKey(
        'catalog.Bundle', on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items'
    )
    title_snapshot = models.CharField(max_length=255, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f'{self.title_snapshot} ({self.order_id})'


class Payment(TimeStampedModel):
    PROVIDER_MANUAL = 'manual'
    PROVIDER_CASH = 'cash'
    PROVIDER_STRIPE = 'stripe'
    PROVIDER_CINETPAY = 'cinetpay'
    PROVIDER_PAYPAL = 'paypal'
    PROVIDER_CHOICES = [
        (PROVIDER_MANUAL, 'Manuel'),
        (PROVIDER_CASH, 'Espèces'),
        (PROVIDER_STRIPE, 'Stripe'),
        (PROVIDER_CINETPAY, 'CinetPay (Mobile Money/Carte)'),
        (PROVIDER_PAYPAL, 'PayPal'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_SUCCEEDED = 'succeeded'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'En attente'), (STATUS_SUCCEEDED, 'Réussi'), (STATUS_FAILED, 'Échoué'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_reference = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='XOF')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    receipt = models.FileField(upload_to='payment_receipts/', null=True, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f'{self.provider} – {self.amount}{self.currency} – {self.status}'


class Payout(TimeStampedModel):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_PAID = 'paid'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'En attente'),
        (STATUS_APPROVED, 'Approuvé'),
        (STATUS_PAID, 'Payé'),
        (STATUS_REJECTED, 'Rejeté'),
    ]

    trainer = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='payouts')
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=30)
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='XOF')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    processed_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'Payout #{self.id} – {self.trainer} – {self.net_amount}{self.currency} ({self.status})'


class PayoutItem(TimeStampedModel):
    payout = models.ForeignKey(Payout, on_delete=models.CASCADE, related_name='items')
    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE, related_name='payout_item')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f'{self.payout} – {self.order_item}'


class Invoice(TimeStampedModel):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='invoice')
    invoice_number = models.CharField(max_length=50, unique=True)
    pdf_file = models.FileField(upload_to='invoices/', null=True, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.invoice_number
