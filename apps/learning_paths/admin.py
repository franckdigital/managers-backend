from django.contrib import admin

from apps.learning_paths.models import (
    LearningPath,
    LearningPathEnrollment,
    LearningPathStep,
    SessionParticipant,
    TrainingSession,
)


class LearningPathStepInline(admin.TabularInline):
    model = LearningPathStep
    extra = 0


@admin.register(LearningPath)
class LearningPathAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'path_type', 'is_active')
    list_filter = ('path_type', 'is_active')
    inlines = [LearningPathStepInline]


@admin.register(LearningPathEnrollment)
class LearningPathEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'path', 'status', 'progress_percent', 'due_date')
    list_filter = ('status',)


class SessionParticipantInline(admin.TabularInline):
    model = SessionParticipant
    extra = 0


@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'trainer', 'start_datetime', 'end_datetime', 'location_type')
    list_filter = ('location_type',)
    inlines = [SessionParticipantInline]
