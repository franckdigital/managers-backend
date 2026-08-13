from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.constants import Roles
from apps.core.permissions import HasRole
from apps.virtual_classes.models import VirtualClass, VirtualClassAttendance, VirtualClassQuestion
from apps.virtual_classes.serializers import (
    AttendanceSignatureSerializer,
    SignAttendanceRequestSerializer,
    VirtualClassAttendanceSerializer,
    VirtualClassQuestionSerializer,
    VirtualClassSerializer,
)
from apps.virtual_classes.services import sign_attendance

IsContentManager = HasRole.for_roles(Roles.TRAINER, Roles.COMPANY_ADMIN, Roles.HR)


class VirtualClassViewSet(viewsets.ModelViewSet):
    queryset = VirtualClass.objects.prefetch_related('attendances', 'questions', 'attendance_signatures').all()
    serializer_class = VirtualClassSerializer
    filterset_fields = ['provider', 'company', 'chapter']

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'join', 'leave', 'ask', 'sign_attendance'):
            return [permissions.IsAuthenticated()]
        return [IsContentManager()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, company=self.request.user.company)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        vclass = self.get_object()
        attendance, _ = VirtualClassAttendance.objects.get_or_create(virtual_class=vclass, user=request.user)
        attendance.joined_at = timezone.now()
        attendance.save(update_fields=['joined_at'])
        return Response({'join_url': vclass.join_url})

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        vclass = self.get_object()
        attendance = VirtualClassAttendance.objects.filter(virtual_class=vclass, user=request.user).first()
        if attendance and attendance.joined_at:
            attendance.left_at = timezone.now()
            attendance.duration_seconds = int((attendance.left_at - attendance.joined_at).total_seconds())
            attendance.save(update_fields=['left_at', 'duration_seconds'])
        return Response(VirtualClassAttendanceSerializer(attendance).data)

    @action(detail=True, methods=['post'])
    def ask(self, request, pk=None):
        vclass = self.get_object()
        question = VirtualClassQuestion.objects.create(
            virtual_class=vclass, user=request.user, question=request.data.get('question', '')
        )
        return Response(VirtualClassQuestionSerializer(question).data, status=201)

    @action(detail=True, methods=['post'], url_path='sign-attendance')
    def sign_attendance(self, request, pk=None):
        vclass = self.get_object()
        if not VirtualClassAttendance.objects.filter(virtual_class=vclass, user=request.user, joined_at__isnull=False).exists():
            return Response({'detail': "Vous devez avoir rejoint la session avant de signer l'attestation."}, status=400)

        serializer = SignAttendanceRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ip_address = request.META.get('REMOTE_ADDR')
        signature = sign_attendance(vclass, request.user, serializer.validated_data['signed_name'], ip_address)
        return Response(AttendanceSignatureSerializer(signature).data, status=201)

    @action(detail=True, methods=['post'], permission_classes=[IsContentManager])
    def answer(self, request, pk=None):
        question = VirtualClassQuestion.objects.get(pk=request.data.get('question_id'))
        question.answer = request.data.get('answer', '')
        question.answered_by = request.user
        question.answered_at = timezone.now()
        question.save(update_fields=['answer', 'answered_by', 'answered_at'])
        return Response(VirtualClassQuestionSerializer(question).data)
