from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.constants import Roles
from apps.core.permissions import HasRole
from apps.gamification.models import Badge, Challenge, ChallengeParticipation, Level
from apps.gamification.serializers import (
    BadgeSerializer,
    ChallengeParticipationSerializer,
    ChallengeSerializer,
    GamificationProfileSerializer,
    LevelSerializer,
)

IsCompanyAdminOrHR = HasRole.for_roles(Roles.COMPANY_ADMIN, Roles.HR)


class LevelViewSet(viewsets.ModelViewSet):
    queryset = Level.objects.all()
    serializer_class = LevelSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [permissions.IsAuthenticated()]
        return [IsCompanyAdminOrHR()]


class BadgeViewSet(viewsets.ModelViewSet):
    queryset = Badge.objects.all()
    serializer_class = BadgeSerializer
    filterset_fields = ['criteria_type', 'company']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [permissions.IsAuthenticated()]
        return [IsCompanyAdminOrHR()]


class ChallengeViewSet(viewsets.ModelViewSet):
    queryset = Challenge.objects.all()
    serializer_class = ChallengeSerializer
    filterset_fields = ['company']

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'join'):
            return [permissions.IsAuthenticated()]
        return [IsCompanyAdminOrHR()]

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        challenge = self.get_object()
        participation, _ = ChallengeParticipation.objects.get_or_create(challenge=challenge, user=request.user)
        return Response(ChallengeParticipationSerializer(participation).data)


class MyGamificationProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(GamificationProfileSerializer(request.user).data)


class LeaderboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from django.db.models import Sum

        from apps.accounts.models import User

        user = request.user
        qs = User.objects.annotate(total_xp=Sum('xp_logs__amount')).exclude(total_xp__isnull=True)
        if not (user.is_superuser or user.role == Roles.SUPER_ADMIN):
            qs = qs.filter(company_id=user.company_id)
        qs = qs.order_by('-total_xp')[:50]
        data = [{'user_id': u.id, 'full_name': u.get_full_name(), 'total_xp': u.total_xp} for u in qs]
        return Response(data)
