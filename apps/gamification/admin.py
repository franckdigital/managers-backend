from django.contrib import admin

from apps.gamification.models import Badge, Challenge, ChallengeParticipation, Level, UserBadge, XPLog


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'min_xp')


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'criteria_type')
    list_filter = ('criteria_type',)


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'badge', 'awarded_at')


@admin.register(XPLog)
class XPLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'reason', 'source_type', 'created_at')


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'start_date', 'end_date', 'xp_reward')


@admin.register(ChallengeParticipation)
class ChallengeParticipationAdmin(admin.ModelAdmin):
    list_display = ('challenge', 'user', 'status', 'completed_at')
