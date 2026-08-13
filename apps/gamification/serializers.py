from rest_framework import serializers

from apps.gamification.models import Badge, Challenge, ChallengeParticipation, Level, UserBadge, XPLog
from apps.gamification.services import get_current_level, get_total_xp


class LevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Level
        fields = '__all__'


class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = '__all__'


class UserBadgeSerializer(serializers.ModelSerializer):
    badge_detail = BadgeSerializer(source='badge', read_only=True)

    class Meta:
        model = UserBadge
        fields = '__all__'


class XPLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = XPLog
        fields = '__all__'


class ChallengeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Challenge
        fields = '__all__'


class ChallengeParticipationSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = ChallengeParticipation
        fields = '__all__'
        read_only_fields = ('user', 'status', 'completed_at')


class GamificationProfileSerializer(serializers.Serializer):
    total_xp = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    badges = serializers.SerializerMethodField()
    streak = serializers.SerializerMethodField()

    def get_total_xp(self, user):
        return get_total_xp(user)

    def get_level(self, user):
        level = get_current_level(user)
        return LevelSerializer(level).data if level else None

    def get_badges(self, user):
        return UserBadgeSerializer(user.badges.select_related('badge'), many=True).data

    def get_streak(self, user):
        streak = getattr(user, 'streak', None)
        return {
            'current': streak.current_streak if streak else 0,
            'longest': streak.longest_streak if streak else 0,
        }
