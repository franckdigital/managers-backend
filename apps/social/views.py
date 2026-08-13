from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.social.models import Conversation, ForumPost, ForumThread, LearningGroup, MentorshipRelation, Message
from apps.social.serializers import (
    ConversationSerializer,
    ForumPostSerializer,
    ForumThreadSerializer,
    LearningGroupSerializer,
    MentorshipRelationSerializer,
    MessageSerializer,
)


class ForumThreadViewSet(viewsets.ModelViewSet):
    queryset = ForumThread.objects.select_related('author', 'course').prefetch_related('posts').all()
    serializer_class = ForumThreadSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['course', 'is_pinned', 'is_closed']
    search_fields = ['title']

    def perform_create(self, serializer):
        serializer.save(author=self.request.user, company=self.request.user.company)


class ForumPostViewSet(viewsets.ModelViewSet):
    queryset = ForumPost.objects.select_related('author', 'thread').all()
    serializer_class = ForumPostSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['thread']

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post'], url_path='mark-solution')
    def mark_solution(self, request, pk=None):
        post = self.get_object()
        if request.user.id != post.thread.author_id:
            raise PermissionDenied("Seul l'auteur de la discussion peut marquer une réponse comme solution.")
        ForumPost.objects.filter(thread=post.thread).update(is_solution=False)
        post.is_solution = True
        post.save(update_fields=['is_solution'])
        return Response(ForumPostSerializer(post).data)


class LearningGroupViewSet(viewsets.ModelViewSet):
    queryset = LearningGroup.objects.prefetch_related('members').all()
    serializer_class = LearningGroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.is_superuser or user.role == 'super_admin':
            return qs
        return qs.filter(company_id=user.company_id)

    def perform_create(self, serializer):
        group = serializer.save(created_by=self.request.user, company=self.request.user.company)
        group.members.add(self.request.user)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        group = self.get_object()
        group.members.add(request.user)
        return Response(LearningGroupSerializer(group).data)

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        group = self.get_object()
        group.members.remove(request.user)
        return Response(LearningGroupSerializer(group).data)


class MentorshipRelationViewSet(viewsets.ModelViewSet):
    serializer_class = MentorshipRelationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status']

    def get_queryset(self):
        user = self.request.user
        return MentorshipRelation.objects.select_related('mentor', 'mentee').filter(Q(mentor=user) | Q(mentee=user))

    def perform_create(self, serializer):
        user = self.request.user
        mentor = serializer.validated_data.get('mentor')
        mentee = serializer.validated_data.get('mentee')
        if user.id not in (getattr(mentor, 'id', None), getattr(mentee, 'id', None)):
            raise PermissionDenied('Vous devez être mentor ou mentoré dans cette relation.')
        serializer.save()

    @action(detail=False, methods=['get'], url_path='available-mentors')
    def available_mentors(self, request):
        from apps.accounts.models import User

        existing_pairs = MentorshipRelation.objects.filter(
            Q(mentor=request.user) | Q(mentee=request.user)
        ).values_list('mentor_id', 'mentee_id')
        excluded_ids = {uid for pair in existing_pairs for uid in pair} | {request.user.id}

        qs = User.objects.filter(company_id=request.user.company_id, is_active=True).exclude(id__in=excluded_ids)
        data = [
            {
                'id': u.id,
                'full_name': u.get_full_name(),
                'role': u.role,
                'department': u.department.name if u.department else None,
            }
            for u in qs[:100]
        ]
        return Response(data)

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        relation = self.get_object()
        if request.user.id != relation.mentor_id:
            raise PermissionDenied('Seul le mentor peut accepter cette demande.')
        relation.status = MentorshipRelation.STATUS_ACTIVE
        relation.started_at = timezone.now().date()
        relation.save(update_fields=['status', 'started_at'])
        return Response(MentorshipRelationSerializer(relation).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        relation = self.get_object()
        relation.status = MentorshipRelation.STATUS_COMPLETED
        relation.save(update_fields=['status'])
        return Response(MentorshipRelationSerializer(relation).data)


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user).prefetch_related('messages', 'participants')

    def perform_create(self, serializer):
        conversation = serializer.save()
        conversation.participants.add(self.request.user)

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        conversation = self.get_object()
        message = Message.objects.create(conversation=conversation, sender=request.user, content=request.data.get('content', ''))
        message.read_by.add(request.user)
        return Response(MessageSerializer(message).data, status=201)

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        conversation = self.get_object()
        for message in conversation.messages.exclude(read_by=request.user):
            message.read_by.add(request.user)
        return Response({'detail': 'ok'})
