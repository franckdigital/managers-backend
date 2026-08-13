from django.contrib import admin

from apps.assessments.models import (
    Assessment,
    AssessmentAttempt,
    AssessmentQuestion,
    AssignmentSubmission,
    AttemptAnswer,
    Question,
    QuestionBank,
    QuestionChoice,
)


class QuestionChoiceInline(admin.TabularInline):
    model = QuestionChoice
    extra = 0


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'bank', 'question_type', 'difficulty', 'points')
    list_filter = ('question_type', 'difficulty')
    inlines = [QuestionChoiceInline]


@admin.register(QuestionBank)
class QuestionBankAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'created_by')


class AssessmentQuestionInline(admin.TabularInline):
    model = AssessmentQuestion
    extra = 0


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'chapter', 'assessment_type', 'passing_score', 'max_attempts', 'is_published')
    list_filter = ('assessment_type', 'is_published', 'is_randomized')
    inlines = [AssessmentQuestionInline]


@admin.register(AssessmentAttempt)
class AssessmentAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'assessment', 'attempt_number', 'score', 'is_passed', 'status', 'started_at')
    list_filter = ('status', 'is_passed')


@admin.register(AttemptAnswer)
class AttemptAnswerAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'question', 'is_correct', 'points_awarded')


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'grade', 'graded_by', 'graded_at')
