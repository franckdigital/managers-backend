from django.contrib import admin

from apps.revenue_share.models import PartnerMonthlyEarning, PartnerPayout, PartnerPayoutItem


@admin.register(PartnerMonthlyEarning)
class PartnerMonthlyEarningAdmin(admin.ModelAdmin):
    list_display = ('course', 'partner', 'year', 'month', 'rate', 'total_revenue', 'earning_amount', 'closed_at')
    list_filter = ('year', 'month')
    search_fields = ('course__title', 'partner__email')


@admin.register(PartnerPayout)
class PartnerPayoutAdmin(admin.ModelAdmin):
    list_display = ('id', 'partner', 'gross_amount', 'status', 'processed_at')
    list_filter = ('status',)


admin.site.register(PartnerPayoutItem)
