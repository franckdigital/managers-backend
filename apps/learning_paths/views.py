from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.constants import Roles
from apps.core.mixins import CompanyScopedViewSetMixin
from apps.core.permissions import HasRole
from apps.learning_paths.models import LearningPath, LearningPathEnrollment, LearningPathStep, SessionParticipant, TrainingSession
from apps.learning_paths.serializers import (
    LearningPathEnrollmentSerializer,
    LearningPathSerializer,
    LearningPathStepSerializer,
    SessionParticipantSerializer,
    TrainingSessionSerializer,
)

IsHRorManager = HasRole.for_roles(Roles.HR, Roles.MANAGER, Roles.COMPANY_ADMIN)


class LearningPathViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = LearningPath.objects.prefetch_related('steps').all()
    serializer_class = LearningPathSerializer
    filterset_fields = ['path_type', 'is_active']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [permissions.IsAuthenticated()]
        return [IsHRorManager()]

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user)


class LearningPathStepViewSet(viewsets.ModelViewSet):
    queryset = LearningPathStep.objects.select_related('path', 'course').all()
    serializer_class = LearningPathStepSerializer
    permission_classes = [IsHRorManager]
    filterset_fields = ['path']


class LearningPathEnrollmentViewSet(viewsets.ModelViewSet):
    serializer_class = LearningPathEnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['path', 'status']
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        qs = LearningPathEnrollment.objects.select_related('path', 'user')
        if user.is_superuser or user.role == Roles.SUPER_ADMIN:
            return qs
        if user.role in (Roles.COMPANY_ADMIN, Roles.HR):
            return qs.filter(user__company_id=user.company_id)
        if user.role == Roles.MANAGER:
            return qs.filter(user__manager=user)
        return qs.filter(user=user)

    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)


class TrainingSessionViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = TrainingSession.objects.select_related('course', 'path', 'trainer').prefetch_related('participants').all()
    serializer_class = TrainingSessionSerializer
    filterset_fields = ['course', 'path', 'trainer', 'location_type']

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'register'):
            return [permissions.IsAuthenticated()]
        return [IsHRorManager()]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and (user.is_superuser or getattr(user, 'role', None) == Roles.SUPER_ADMIN):
            return qs
        if self.action in ('list', 'retrieve', 'register') and user.is_authenticated and not user.company_id:
            qs = TrainingSession.objects.select_related('course', 'path', 'trainer').prefetch_related('participants')
            return qs.filter(company__isnull=True)
        return qs

    @action(detail=True, methods=['post'])
    def register(self, request, pk=None):
        session = self.get_object()
        already = SessionParticipant.objects.filter(session=session, user=request.user).exclude(
            status=SessionParticipant.STATUS_CANCELLED
        ).first()
        if already:
            return Response(SessionParticipantSerializer(already).data)

        if session.capacity is not None:
            active_count = SessionParticipant.objects.filter(session=session).exclude(
                status=SessionParticipant.STATUS_CANCELLED
            ).count()
            if active_count >= session.capacity:
                return Response({'detail': 'Cette session est complète.'}, status=409)

        participant, _ = SessionParticipant.objects.update_or_create(
            session=session, user=request.user, defaults={'status': SessionParticipant.STATUS_REGISTERED}
        )

        from apps.notifications.services import notify_user

        notify_user(
            request.user,
            'Inscription confirmée',
            f"Votre inscription à la session « {session.title} » du {session.start_datetime:%d/%m/%Y %H:%M} est confirmée.",
            data={'session_id': session.id},
        )
        return Response(SessionParticipantSerializer(participant).data)

    @action(detail=True, methods=['post'])
    def unregister(self, request, pk=None):
        session = self.get_object()
        participant = SessionParticipant.objects.filter(session=session, user=request.user).exclude(
            status=SessionParticipant.STATUS_CANCELLED
        ).first()
        if not participant:
            return Response({'detail': 'Vous n\'êtes pas inscrit à cette session.'}, status=400)
        participant.status = SessionParticipant.STATUS_CANCELLED
        participant.save(update_fields=['status'])

        from apps.notifications.services import notify_user

        notify_user(
            request.user,
            'Désinscription enregistrée',
            f"Votre désinscription de la session « {session.title} » a été prise en compte.",
            data={'session_id': session.id},
        )
        return Response({'detail': 'Désinscription effectuée.'})
