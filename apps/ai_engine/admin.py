from django.contrib import admin

from apps.ai_engine.models import AIConversation, AIGeneratedQuiz, AIMessage, CourseRecommendation, DifficultyAlert


class AIMessageInline(admin.TabularInline):
    model = AIMessage
    extra = 0


@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'title', 'updated_at')
    inlines = [AIMessageInline]


@admin.register(AIGeneratedQuiz)
class AIGeneratedQuizAdmin(admin.ModelAdmin):
    list_display = ('course', 'chapter', 'created_by', 'created_at')


@admin.register(CourseRecommendation)
class CourseRecommendationAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'score', 'reason')


@admin.register(DifficultyAlert)
class DifficultyAlertAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'signal_type', 'is_resolved', 'created_at')
    list_filter = ('signal_type', 'is_resolved')
