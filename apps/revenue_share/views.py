from django.db.models import Sum
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.constants import Roles
from apps.core.permissions import HasRole, IsSuperAdmin
from apps.revenue_share.models import PartnerMonthlyEarning, PartnerPayout
from apps.revenue_share.serializers import PartnerMonthlyEarningSerializer, PartnerPayoutSerializer
from apps.revenue_share.services import (
    approve_partner_payout,
    catalog_period_totals,
    compute_period,
    mark_partner_payout_paid,
    partner_unpaid_earnings,
    reject_partner_payout,
    request_partner_payout,
)

IsAdminOverseer = HasRole.for_roles(Roles.SUPER_ADMIN, Roles.COMPANY_ADMIN, Roles.TRAINING_CENTER_ADMIN)


class PartnerMonthlyEarningViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PartnerMonthlyEarningSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['course', 'partner', 'year', 'month']

    def get_queryset(self):
        user = self.request.user
        qs = PartnerMonthlyEarning.objects.select_related('course', 'partner')
        if user.is_superuser or user.role == Roles.SUPER_ADMIN or user.role in (
            Roles.COMPANY_ADMIN, Roles.TRAINING_CENTER_ADMIN
        ):
            return qs
        return qs.filter(partner=user)

    @action(detail=False, methods=['get'])
    def aggregate(self, request):
        """Cumule les gains sur un/plusieurs cours ou tout le catalogue, sur une plage
        de mois — sert le besoin de « cumul sur un et plusieurs cours ou l'ensemble du
        catalogue » explicitement demandé."""
        qs = self.filter_queryset(self.get_queryset())
        totals = qs.aggregate(
            total_revenue=Sum('total_revenue'),
            total_earning=Sum('earning_amount'),
            total_views=Sum('view_count'),
            total_clicks=Sum('click_count'),
        )
        return Response({
            'total_revenue': totals['total_revenue'] or 0,
            'total_earning': totals['total_earning'] or 0,
            'total_views': totals['total_views'] or 0,
            'total_clicks': totals['total_clicks'] or 0,
            'course_count': qs.values('course').distinct().count(),
        })


class MyRevenueShareDashboardView(APIView):
    """GET /revenue-share/my-dashboard/ — stats du mois courant + historique + détail
    par cours, pour le partenaire (ou l'auteur admin, à titre informatif) connecté."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        qs = PartnerMonthlyEarning.objects.filter(partner=request.user).select_related('course')

        current_month = qs.filter(year=today.year, month=today.month)
        current_totals = current_month.aggregate(
            revenue=Sum('total_revenue'), earning=Sum('earning_amount'),
            views=Sum('view_count'), clicks=Sum('click_count'),
        )
        history = qs.order_by('-year', '-month')[:12]

        return Response({
            'current_month': {
                'year': today.year, 'month': today.month,
                'total_revenue': current_totals['revenue'] or 0,
                'total_earning': current_totals['earning'] or 0,
                'total_views': current_totals['views'] or 0,
                'total_clicks': current_totals['clicks'] or 0,
                'courses': PartnerMonthlyEarningSerializer(current_month, many=True).data,
            },
            'history': PartnerMonthlyEarningSerializer(history, many=True).data,
        })


class ClosePeriodView(APIView):
    """POST /revenue-share/close-period/ {year, month} — équivalent UI de la commande
    de gestion `close_partner_earnings_period`, pour un admin qui préfère un bouton."""

    permission_classes = [IsSuperAdmin]

    def post(self, request):
        year = request.data.get('year')
        month = request.data.get('month')
        if not year or not month:
            return Response({'detail': 'year et month requis.'}, status=400)
        try:
            results = compute_period(int(year), int(month))
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=400)
        return Response({'closed_courses': len(results)})


class CatalogTotalsView(APIView):
    permission_classes = [IsAdminOverseer]

    def get(self, request):
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        if not year or not month:
            return Response({'detail': 'year et month requis.'}, status=400)
        return Response(catalog_period_totals(int(year), int(month)))


class EligibleRecipientsView(APIView):
    """GET /revenue-share/eligible-recipients/ — liste pour le sélecteur « auteur (admin)
    ou partenaire » de l'éditeur de cours."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.accounts.models import User

        users = User.objects.filter(
            role__in=Roles.REVENUE_SHARE_ELIGIBLE_ROLES, is_active=True
        ).order_by('first_name', 'last_name')
        return Response([
            {
                'id': u.id,
                'name': u.get_full_name() or u.email,
                'role': u.role,
                'partner_default_rate': u.partner_default_rate,
            }
            for u in users
        ])


class PartnerPayoutViewSet(viewsets.ModelViewSet):
    serializer_class = PartnerPayoutSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'partner']
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        qs = PartnerPayout.objects.select_related('partner').prefetch_related('items')
        if user.is_superuser or user.role == Roles.SUPER_ADMIN:
            return qs
        if user.role in (Roles.COMPANY_ADMIN, Roles.TRAINING_CENTER_ADMIN):
            return qs
        return qs.filter(partner=user)

    def create(self, request, *args, **kwargs):
        if request.user.role != Roles.PARTNER:
            return Response({'detail': 'Seuls les partenaires peuvent demander un paiement.'}, status=403)
        try:
            payout = request_partner_payout(request.user)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=400)
        return Response(PartnerPayoutSerializer(payout).data, status=201)

    @action(detail=False, methods=['get'], url_path='unpaid-earnings')
    def unpaid_earnings(self, request):
        if request.user.role != Roles.PARTNER:
            return Response({'detail': 'Réservé aux partenaires.'}, status=403)
        items = partner_unpaid_earnings(request.user)
        total = sum((item.earning_amount for item in items), start=0)
        return Response({'pending_items': items.count(), 'gross_amount': str(total)})

    @action(detail=True, methods=['post'], permission_classes=[HasRole.for_roles(Roles.SUPER_ADMIN, Roles.COMPANY_ADMIN)])
    def approve(self, request, pk=None):
        payout = self.get_object()
        return Response(PartnerPayoutSerializer(approve_partner_payout(payout, request.user)).data)

    @action(detail=True, methods=['post'], url_path='mark-paid', permission_classes=[HasRole.for_roles(Roles.SUPER_ADMIN, Roles.COMPANY_ADMIN)])
    def mark_paid(self, request, pk=None):
        payout = self.get_object()
        return Response(PartnerPayoutSerializer(mark_partner_payout_paid(payout, request.user)).data)

    @action(detail=True, methods=['post'], permission_classes=[HasRole.for_roles(Roles.SUPER_ADMIN, Roles.COMPANY_ADMIN)])
    def reject(self, request, pk=None):
        payout = self.get_object()
        return Response(
            PartnerPayoutSerializer(reject_partner_payout(payout, request.user, request.data.get('notes', ''))).data
        )
