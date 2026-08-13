from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.gamification.views import (
    BadgeViewSet,
    ChallengeViewSet,
    LeaderboardView,
    LevelViewSet,
    MyGamificationProfileView,
)

router = DefaultRouter()
router.register('levels', LevelViewSet, basename='level')
router.register('badges', BadgeViewSet, basename='badge')
router.register('challenges', ChallengeViewSet, basename='challenge')

urlpatterns = [
    path('profile/', MyGamificationProfileView.as_view(), name='gamification-profile'),
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
] + router.urls
