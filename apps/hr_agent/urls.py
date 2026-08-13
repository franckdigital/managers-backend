from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.hr_agent.views import (
    AgentChatView,
    AgentResourcesMenuView,
    AgentResourceViewSet,
    JobDescriptionGenerateView,
)

router = DefaultRouter()
router.register('resources', AgentResourceViewSet, basename='hr-agent-resource')

urlpatterns = [
    path('chat/', AgentChatView.as_view(), name='hr-agent-chat'),
    path('resources/menu/', AgentResourcesMenuView.as_view(), name='hr-agent-resources-menu'),
    path('job-description/', JobDescriptionGenerateView.as_view(), name='hr-agent-job-description'),
] + router.urls
