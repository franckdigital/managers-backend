from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.tenants.views import (
    B2CSubscribeView,
    CompanySubscriptionViewSet,
    CompanyViewSet,
    DepartmentViewSet,
    ServiceViewSet,
    SubscriptionPlanViewSet,
    TeamViewSet,
    UserSubscriptionViewSet,
)

router = DefaultRouter()
router.register('plans', SubscriptionPlanViewSet, basename='subscription-plan')
router.register('companies', CompanyViewSet, basename='company')
router.register('subscriptions', CompanySubscriptionViewSet, basename='company-subscription')
router.register('user-subscriptions', UserSubscriptionViewSet, basename='user-subscription')
router.register('departments', DepartmentViewSet, basename='department')
router.register('services', ServiceViewSet, basename='service')
router.register('teams', TeamViewSet, basename='team')

urlpatterns = router.urls + [
    path('b2c-subscribe/', B2CSubscribeView.as_view(), name='b2c-subscribe'),
]
