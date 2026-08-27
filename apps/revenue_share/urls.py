from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.revenue_share.views import (
    CatalogTotalsView,
    ClosePeriodView,
    EligibleRecipientsView,
    MyRevenueShareDashboardView,
    PartnerMonthlyEarningViewSet,
    PartnerPayoutViewSet,
)

router = DefaultRouter()
router.register('partner-monthly-earnings', PartnerMonthlyEarningViewSet, basename='partner-monthly-earning')
router.register('partner-payouts', PartnerPayoutViewSet, basename='partner-payout')

urlpatterns = [
    path('my-dashboard/', MyRevenueShareDashboardView.as_view(), name='revenue-share-my-dashboard'),
    path('close-period/', ClosePeriodView.as_view(), name='revenue-share-close-period'),
    path('eligible-recipients/', EligibleRecipientsView.as_view(), name='revenue-share-eligible-recipients'),
    path('catalog-totals/', CatalogTotalsView.as_view(), name='revenue-share-catalog-totals'),
] + router.urls
