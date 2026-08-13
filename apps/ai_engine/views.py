from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_engine.models import AIConversation, AIGeneratedQuiz, AIMessage, CourseRecommendation, DifficultyAlert
from apps.ai_engine.providers import get_ai_provider
from apps.ai_engine.serializers import (
    AIConversationSerializer,
    AIGeneratedQuizSerializer,
    ChatRequestSerializer,
    CourseRecommendationSerializer,
    DifficultyAlertSerializer,
    GenerateQuizRequestSerializer,
    SummarizeRequestSerializer,
    TranslateRequestSerializer,
)
from apps.ai_engine.services import detect_learning_difficulties, generate_recommendations_for_user
from apps.core.constants import Roles
from apps.core.permissions import HasRole

IsHRorManager = HasRole.for_roles(Roles.HR, Roles.MANAGER, Roles.COMPANY_ADMIN)


class AIConversationViewSet(viewsets.ModelViewSet):
    serializer_class = AIConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AIConversation.objects.filter(user=self.request.user).prefetch_related('messages')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ChatView(APIView):
    """Lot 9 — tutorat intelligent: conversational assistant scoped to a course."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data.get('conversation_id'):
            conversation = AIConversation.objects.get(pk=data['conversation_id'], user=request.user)
        else:
            conversation = AIConversation.objects.create(
                user=request.user, course_id=data.get('course_id'), title=data['message'][:80]
            )

        AIMessage.objects.create(conversation=conversation, role=AIMessage.ROLE_USER, content=data['message'])
        history = [{'role': m.role, 'content': m.content} for m in conversation.messages.all()]

        context = conversation.course.title if conversation.course else ''
        reply = get_ai_provider().chat(history, context=context)

        AIMessage.objects.create(conversation=conversation, role=AIMessage.ROLE_ASSISTANT, content=reply)
        return Response(AIConversationSerializer(conversation).data)


class SummarizeView(APIView):
    """Lot 9 — résumé automatique des vidéos/cours."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SummarizeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        summary = get_ai_provider().summarize(serializer.validated_data['text'])
        return Response({'summary': summary})


class GenerateQuizView(APIView):
    """Lot 9 — création automatique de quiz à partir d'un contenu de cours."""

    permission_classes = [IsHRorManager]

    def post(self, request):
        from apps.courses.models import Chapter, Course

        serializer = GenerateQuizRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        questions = get_ai_provider().generate_quiz(data['content'], data['num_questions'])
        quiz = AIGeneratedQuiz.objects.create(
            course=Course.objects.get(pk=data['course_id']),
            chapter=Chapter.objects.filter(pk=data.get('chapter_id')).first(),
            created_by=request.user,
            source_text=data['content'],
            generated_questions=questions,
        )
        return Response(AIGeneratedQuizSerializer(quiz).data)


class TranslateView(APIView):
    """Lot 9 — traduction / sous-titrage automatique."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = TranslateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        translated = get_ai_provider().translate(**serializer.validated_data)
        return Response({'translated_text': translated})


class RecommendationsView(APIView):
    """Lot 9 — recommandation de formations personnalisée."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        recommendations = generate_recommendations_for_user(request.user)
        return Response(CourseRecommendationSerializer(recommendations, many=True).data)


class DifficultyAlertViewSet(viewsets.ReadOnlyModelViewSet):
    """Lot 9 — détection des difficultés / analyse comportementale."""

    serializer_class = DifficultyAlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['course', 'signal_type', 'is_resolved']

    def get_queryset(self):
        user = self.request.user
        qs = DifficultyAlert.objects.select_related('user', 'course')
        if user.is_superuser or user.role in (Roles.SUPER_ADMIN, Roles.HR, Roles.COMPANY_ADMIN):
            return qs
        if user.role == Roles.MANAGER:
            return qs.filter(user__manager=user)
        return qs.filter(user=user)

    def list(self, request, *args, **kwargs):
        detect_learning_difficulties(request.user)
        return super().list(request, *args, **kwargs)
