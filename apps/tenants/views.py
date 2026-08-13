from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.mixins import AuditLogMixin, CompanyScopedViewSetMixin
from apps.core.permissions import IsCompanyAdmin, IsSuperAdmin
from apps.tenants.models import Company, CompanySubscription, Department, Service, SubscriptionPlan, Team, UserSubscription
from apps.tenants.serializers import (
    CompanySerializer,
    CompanySubscriptionSerializer,
    DepartmentSerializer,
    ServiceSerializer,
    SubscriptionPlanSerializer,
    TeamSerializer,
    UserSubscriptionSerializer,
)


class SubscriptionPlanViewSet(AuditLogMixin, viewsets.ModelViewSet):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsSuperAdmin]

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsSuperAdmin()]


class CompanyViewSet(AuditLogMixin, viewsets.ModelViewSet):
    """Managed exclusively by the super admin: company creation, subscription management."""

    queryset = Company.objects.select_related('plan').all()
    serializer_class = CompanySerializer
    permission_classes = [IsSuperAdmin]
    search_fields = ['name', 'email', 'sector', 'country']
    filterset_fields = ['subscription_status', 'is_active', 'sector', 'country']

    def get_permissions(self):
        if self.action in ('retrieve', 'list', 'tree', 'subscribe'):
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and not (user.is_superuser or user.role == 'super_admin'):
            company = user.company
            if company is None:
                return qs.none()
            return qs.filter(id__in=company.get_descendant_ids())
        return qs

    @action(detail=True, methods=['get'])
    def tree(self, request, pk=None):
        """The company plus its direct subsidiaries, for building a UI tree without client-side recursion."""
        company = self.get_object()
        data = CompanySerializer(company, context={'request': request}).data
        data['subsidiaries'] = CompanySerializer(
            company.subsidiaries.all(), many=True, context={'request': request}
        ).data
        return Response(data)

    @action(detail=True, methods=['post'])
    def subscribe(self, request, pk=None):
        """Company admin initiates a subscription payment; super admin can use provider='manual'."""
        from apps.payments.services import create_subscription_order, initiate_payment, mark_order_paid
        from apps.payments.serializers import OrderSerializer

        company = self.get_object()
        user = request.user
        if not (user.is_superuser or user.role == 'super_admin' or
                (user.role == 'company_admin' and user.company_id == company.id)):
            return Response({'detail': 'Accès refusé.'}, status=403)

        plan_id = request.data.get('plan')
        provider = request.data.get('provider', 'cinetpay')
        if not plan_id:
            return Response({'detail': 'plan requis.'}, status=400)

        try:
            plan = SubscriptionPlan.objects.get(pk=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({'detail': 'Plan introuvable ou inactif.'}, status=404)

        order = create_subscription_order(user, company, plan)
        payment, result = initiate_payment(order, provider)

        if provider == 'manual':
            mark_order_paid(order)
            order.refresh_from_db()

        return Response({
            'order': OrderSerializer(order).data,
            'redirect_url': result.redirect_url,
        }, status=201)

    @action(detail=True, methods=['post'], url_path='activate-subscription')
    def activate_subscription(self, request, pk=None):
        """Super admin manually activates a subscription without going through payment."""
        from apps.tenants.services import activate_company_subscription

        if not (request.user.is_superuser or request.user.role == 'super_admin'):
            return Response({'detail': 'Réservé au super admin.'}, status=403)

        company = self.get_object()
        plan_id = request.data.get('plan')
        end_date = request.data.get('end_date') or None

        if not plan_id:
            return Response({'detail': 'plan requis.'}, status=400)

        try:
            plan = SubscriptionPlan.objects.get(pk=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({'detail': 'Plan introuvable ou inactif.'}, status=404)

        activate_company_subscription(company, plan, end_date=end_date)
        company.refresh_from_db()
        return Response(CompanySerializer(company, context={'request': request}).data)


class CompanySubscriptionViewSet(AuditLogMixin, viewsets.ModelViewSet):
    queryset = CompanySubscription.objects.select_related('company', 'plan').all()
    serializer_class = CompanySubscriptionSerializer
    permission_classes = [IsSuperAdmin]
    filterset_fields = ['company', 'status']


class UserSubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """Individual B2C learner subscriptions — read-only for the learner, full access for super admin."""
    serializer_class = UserSubscriptionSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'plan']

    def get_queryset(self):
        user = self.request.user
        qs = UserSubscription.objects.select_related('plan', 'user')
        if user.is_superuser or user.role == 'super_admin':
            return qs
        return qs.filter(user=user)


class B2CSubscribeView(APIView):
    """B2C learner subscribes to a centre-de-formation plan (cash or mobile money)."""
    permission_classes = [IsAuthenticated]
    parser_classes = None  # accept both JSON and multipart

    def get_parsers(self):
        from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
        return [MultiPartParser(), FormParser(), JSONParser()]

    def post(self, request):
        if request.user.company_id:
            return Response({'detail': 'Réservé aux apprenants individuels sans entreprise.'}, status=403)

        plan_id = request.data.get('plan')
        provider = request.data.get('provider', 'cash')

        if not plan_id:
            return Response({'detail': 'plan requis.'}, status=400)

        try:
            plan = SubscriptionPlan.objects.get(pk=plan_id, plan_type=SubscriptionPlan.PLAN_TYPE_B2C, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({'detail': 'Plan introuvable ou inactif.'}, status=404)

        from apps.payments.services import create_subscription_order, initiate_payment, mark_order_paid
        from apps.payments.serializers import OrderSerializer

        order = create_subscription_order(request.user, None, plan)

        try:
            payment, result = initiate_payment(order, provider)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error('B2CSubscribe payment error [%s]: %s', provider, exc, exc_info=True)
            order.delete()
            return Response({'detail': str(exc)}, status=400)

        # Attach proof file for cash payments
        proof = request.FILES.get('payment_proof')
        if proof and provider == 'cash':
            payment.receipt = proof
            payment.save(update_fields=['receipt'])

        if provider == 'manual':
            mark_order_paid(order)
            order.refresh_from_db()

        return Response({
            'order': OrderSerializer(order).data,
            'redirect_url': result.redirect_url,
            'pending_validation': provider == 'cash',
        }, status=201)


class DepartmentViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsCompanyAdmin]


class ServiceViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Service.objects.select_related('department').all()
    serializer_class = ServiceSerializer
    permission_classes = [IsCompanyAdmin]
    filterset_fields = ['department']


class TeamViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Team.objects.select_related('service', 'manager').all()
    serializer_class = TeamSerializer
    permission_classes = [IsCompanyAdmin]
    filterset_fields = ['service', 'manager']
