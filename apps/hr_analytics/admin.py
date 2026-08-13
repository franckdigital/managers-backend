from django.contrib import admin

from apps.hr_analytics.models import (
    CourseSkill,
    EmployeeSkill,
    Evaluation360Campaign,
    Evaluation360Response,
    IndividualDevelopmentPlan,
    JobRole,
    JobRoleSkillRequirement,
    PDIObjective,
    Skill,
    TrainingBudgetEntry,
)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'category')


@admin.register(CourseSkill)
class CourseSkillAdmin(admin.ModelAdmin):
    list_display = ('course', 'skill', 'level_gained')


class JobRoleSkillRequirementInline(admin.TabularInline):
    model = JobRoleSkillRequirement
    extra = 0


@admin.register(JobRole)
class JobRoleAdmin(admin.ModelAdmin):
    list_display = ('title', 'company')
    inlines = [JobRoleSkillRequirementInline]


@admin.register(EmployeeSkill)
class EmployeeSkillAdmin(admin.ModelAdmin):
    list_display = ('user', 'skill', 'level', 'source', 'last_assessed_at')
    list_filter = ('source',)


class PDIObjectiveInline(admin.TabularInline):
    model = PDIObjective
    extra = 0


@admin.register(IndividualDevelopmentPlan)
class IndividualDevelopmentPlanAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_by', 'period_start', 'period_end', 'status')
    inlines = [PDIObjectiveInline]


class Evaluation360ResponseInline(admin.TabularInline):
    model = Evaluation360Response
    extra = 0


@admin.register(Evaluation360Campaign)
class Evaluation360CampaignAdmin(admin.ModelAdmin):
    list_display = ('title', 'target_user', 'company', 'status', 'period_start', 'period_end')
    inlines = [Evaluation360ResponseInline]


@admin.register(TrainingBudgetEntry)
class TrainingBudgetEntryAdmin(admin.ModelAdmin):
    list_display = ('company', 'year', 'amount_allocated', 'amount_spent')
