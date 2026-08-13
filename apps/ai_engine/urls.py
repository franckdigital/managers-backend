from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.ai_engine.views import (
    AIConversationViewSet,
    ChatView,
    DifficultyAlertViewSet,
    GenerateQuizView,
    RecommendationsView,
    SummarizeView,
    TranslateView,
)

router = DefaultRouter()
router.register('conversations', AIConversationViewSet, basename='ai-conversation')
router.register('difficulty-alerts', DifficultyAlertViewSet, basename='difficulty-alert')

urlpatterns = [
    path('chat/', ChatView.as_view(), name='ai-chat'),
    path('summarize/', SummarizeView.as_view(), name='ai-summarize'),
    path('generate-quiz/', GenerateQuizView.as_view(), name='ai-generate-quiz'),
    path('translate/', TranslateView.as_view(), name='ai-translate'),
    path('recommendations/', RecommendationsView.as_view(), name='ai-recommendations'),
] + router.urls
