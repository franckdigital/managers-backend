from django.contrib import admin

from apps.progression.models import ChapterUnlock, ChapterValidation, CourseProgressionSettings, LessonProgress, XAPIStatement


@admin.register(CourseProgressionSettings)
class CourseProgressionSettingsAdmin(admin.ModelAdmin):
    list_display = ('course', 'sequential_enabled', 'min_video_watch_percent', 'quiz_required', 'min_passing_score')


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'is_completed', 'watch_percent', 'document_viewed')
    list_filter = ('is_completed', 'document_viewed')


@admin.register(ChapterUnlock)
class ChapterUnlockAdmin(admin.ModelAdmin):
    list_display = ('user', 'chapter', 'unlocked_at')


@admin.register(ChapterValidation)
class ChapterValidationAdmin(admin.ModelAdmin):
    list_display = ('user', 'chapter', 'validated_by', 'created_at')


@admin.register(XAPIStatement)
class XAPIStatementAdmin(admin.ModelAdmin):
    list_display = ('user', 'verb', 'object_type', 'object_id', 'timestamp')
    list_filter = ('verb',)
