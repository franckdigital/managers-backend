from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.mixins import AuditLogMixin, CompanyScopedViewSetMixin
from apps.core.permissions import IsCompanyAdmin, IsHR, IsSuperAdmin
from apps.tenants.models import (
    Company, CompanySubscription, Department, Service, SubscriptionPlan,
    Team, TeamSubscription, UserSubscription,
)
from apps.tenants.serializers import (
    CompanySerializer,
    CompanySubscriptionSerializer,
    DepartmentSerializer,
    ServiceSerializer,
    SubscriptionPlanSerializer,
    TeamSerializer,
    TeamSubscriptionSerializer,
    UserSubscriptionSerializer,
)


def _company_tree_ids(user):
    """Ids of the user's company plus all its subsidiaries (empty if no company)."""
    company = getattr(user, 'company', None)
    return company.get_descendant_ids() if company is not None else set()


def _can_manage_subscription_for(user, company_id):
    """True when the user may pay a subscription for the given company id: super admin, or
    a company admin / DRH (hr) whose own company owns that company (directly or via a
    parent). Paying (Mobile Money or cash) is allowed for the DRH; only the super admin can
    activate a subscription for free without a payment order (see `activate_subscription`)."""
    if user.is_superuser or user.role == 'super_admin':
        return True
    if user.role not in ('company_admin', 'training_center_admin', 'hr'):
        return False
    return company_id in _company_tree_ids(user)


def _start_subscription_payment(user, order, provider):
    """Kick off payment for a subscription order (company/site or team), mirroring
    B2CSubscribeView's error handling. Returns (result, error_response); on any
    failure the pending order is deleted and error_response is a DRF Response."""
    from apps.payments.services import initiate_payment, mark_order_paid

    if provider == 'cinetpay' and not getattr(user, 'phone', ''):
        order.delete()
        return None, Response(
            {'detail': "Renseignez un numéro de téléphone mobile dans votre profil avant de payer par Mobile Money."},
            status=400,
        )

    try:
        _, result = initiate_payment(order, provider)
    except Exception as exc:  # noqa: BLE001 — surface the gateway message to the caller
        import logging
        logging.getLogger(__name__).error('Subscription payment error [%s]: %s', provider, exc, exc_info=True)
        order.delete()
        return None, Response({'detail': str(exc)}, status=400)

    if provider == 'manual':
        mark_order_paid(order)
        order.refresh_from_db()

    return result, None


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
        """Company/site subscription payment. Allowed for super admin and for an
        admin/HR of the company (or a parent company). provider: cinetpay | cash | manual."""
        from apps.payments.services import create_subscription_order
        from apps.payments.serializers import OrderSerializer

        company = self.get_object()
        user = request.user
        if not _can_manage_subscription_for(user, company.id):
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
        result, error = _start_subscription_payment(user, order, provider)
        if error is not None:
            return error

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

        if provider == 'cinetpay' and not request.user.phone:
            return Response(
                {'detail': 'Veuillez renseigner votre numéro de téléphone dans votre profil avant de payer par Mobile Money.'},
                status=400,
            )

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
    queryset = Department.objects.select_related('company').all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsCompanyAdmin]
    filterset_fields = ['company']


class ServiceViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Service.objects.select_related('department', 'company').all()
    serializer_class = ServiceSerializer
    permission_classes = [IsCompanyAdmin]
    filterset_fields = ['company', 'department']


class TeamViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Team.objects.select_related('service', 'manager', 'plan', 'company').all()
    serializer_class = TeamSerializer
    permission_classes = [IsCompanyAdmin]
    filterset_fields = ['company', 'service', 'manager', 'subscription_status']

    def get_permissions(self):
        # The DRH (hr) may browse teams and pay a team subscription, but not
        # create/rename/delete teams nor activate a subscription for free.
        if self.action in ('list', 'retrieve', 'subscribe'):
            return [IsHR()]
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def subscribe(self, request, pk=None):
        """Company admin or DRH initiates a subscription payment for a single team.
        provider: cinetpay | cash | manual."""
        from apps.payments.services import create_subscription_order
        from apps.payments.serializers import OrderSerializer

        team = self.get_object()
        if not _can_manage_subscription_for(request.user, team.company_id):
            return Response({'detail': 'Accès refusé.'}, status=403)

        plan_id = request.data.get('plan')
        provider = request.data.get('provider', 'cinetpay')
        if not plan_id:
            return Response({'detail': 'plan requis.'}, status=400)

        try:
            plan = SubscriptionPlan.objects.get(pk=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({'detail': 'Plan introuvable ou inactif.'}, status=404)

        order = create_subscription_order(request.user, None, plan, team=team)
        result, error = _start_subscription_payment(request.user, order, provider)
        if error is not None:
            return error

        return Response({
            'order': OrderSerializer(order).data,
            'redirect_url': result.redirect_url,
        }, status=201)

    @action(detail=True, methods=['post'], url_path='activate-subscription')
    def activate_subscription(self, request, pk=None):
        """Super admin manually activates a team subscription without going through payment."""
        from apps.tenants.services import activate_team_subscription

        if not (request.user.is_superuser or request.user.role == 'super_admin'):
            return Response({'detail': 'Réservé au super admin.'}, status=403)

        team = self.get_object()
        plan_id = request.data.get('plan')
        end_date = request.data.get('end_date') or None
        if not plan_id:
            return Response({'detail': 'plan requis.'}, status=400)

        try:
            plan = SubscriptionPlan.objects.get(pk=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({'detail': 'Plan introuvable ou inactif.'}, status=404)

        activate_team_subscription(team, plan, end_date=end_date)
        team.refresh_from_db()
        return Response(TeamSerializer(team, context={'request': request}).data)


class TeamSubscriptionViewSet(AuditLogMixin, viewsets.ReadOnlyModelViewSet):
    queryset = TeamSubscription.objects.select_related('team', 'plan').all()
    serializer_class = TeamSubscriptionSerializer
    permission_classes = [IsSuperAdmin]
    filterset_fields = ['team', 'status']
