from django.db import models

from apps.core.models import TimeStampedModel


class PartnerMonthlyEarning(TimeStampedModel):
    """Immutable snapshot of what a course earned its revenue_partner for one calendar
    month — computed once at period close (apps.revenue_share.services.compute_period)
    and never recalculated afterwards, even if the course's partner/rate later changes."""

    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='partner_earnings')
    partner = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='partner_earnings')
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()  # 1-12

    rate = models.DecimalField(max_digits=5, decimal_places=2)  # snapshot of Course.revenue_share_rate at close time

    direct_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    subscription_share_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bundle_share_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    earning_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    view_count = models.PositiveIntegerField(default=0)
    click_count = models.PositiveIntegerField(default=0)

    currency = models.CharField(max_length=3, default='XOF')
    closed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('course', 'year', 'month')
        ordering = ['-year', '-month']

    def __str__(self):
        return f'{self.course} — {self.year}/{self.month:02d} — {self.partner} — {self.earning_amount}{self.currency}'


class PartnerPayout(TimeStampedModel):
    """Mirrors apps.payments.Payout in shape/workflow, but kept as a separate model —
    Payout/PayoutItem's OneToOneField(OrderItem) invariant ("an OrderItem is claimed at
    most once, ever") is load-bearing for the trainer flow already in production, and
    partner earnings have no OrderItem behind them (they're computed, not purchased)."""

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

    partner = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='partner_payouts')
    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='XOF')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    processed_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'PartnerPayout #{self.id} – {self.partner} – {self.gross_amount}{self.currency} ({self.status})'


class PartnerPayoutItem(TimeStampedModel):
    payout = models.ForeignKey(PartnerPayout, on_delete=models.CASCADE, related_name='items')
    earning = models.OneToOneField(PartnerMonthlyEarning, on_delete=models.CASCADE, related_name='payout_item')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f'{self.payout} – {self.earning}'
