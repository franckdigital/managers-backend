from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.hr_analytics.views import (
    B2CDashboardView,
    CourseKPIView,
    CourseSkillViewSet,
    EmployeeKPIView,
    EmployeeSkillViewSet,
    Evaluation360CampaignViewSet,
    Evaluation360ResponseViewSet,
    ExecutiveDashboardView,
    HRDashboardExportView,
    HRDashboardView,
    IndividualDevelopmentPlanViewSet,
    JobRoleSkillRequirementViewSet,
    JobRoleViewSet,
    ManagerDashboardView,
    PDIObjectiveViewSet,
    SkillGapView,
    SkillViewSet,
    TrainingBudgetEntryViewSet,
)

router = DefaultRouter()
router.register('skills', SkillViewSet, basename='skill')
router.register('course-skills', CourseSkillViewSet, basename='course-skill')
router.register('job-roles', JobRoleViewSet, basename='job-role')
router.register('job-role-requirements', JobRoleSkillRequirementViewSet, basename='job-role-requirement')
router.register('employee-skills', EmployeeSkillViewSet, basename='employee-skill')
router.register('development-plans', IndividualDevelopmentPlanViewSet, basename='development-plan')
router.register('pdi-objectives', PDIObjectiveViewSet, basename='pdi-objective')
router.register('evaluation-360-campaigns', Evaluation360CampaignViewSet, basename='evaluation-360-campaign')
router.register('evaluation-360-responses', Evaluation360ResponseViewSet, basename='evaluation-360-response')
router.register('training-budgets', TrainingBudgetEntryViewSet, basename='training-budget')

urlpatterns = [
    path('dashboard/employee/', EmployeeKPIView.as_view(), name='kpi-employee-me'),
    path('dashboard/employee/<int:user_id>/', EmployeeKPIView.as_view(), name='kpi-employee'),
    path('dashboard/manager/', ManagerDashboardView.as_view(), name='kpi-manager'),
    path('dashboard/hr/', HRDashboardView.as_view(), name='kpi-hr'),
    path('dashboard/hr/export/', HRDashboardExportView.as_view(), name='kpi-hr-export'),
    path('dashboard/executive/', ExecutiveDashboardView.as_view(), name='kpi-executive'),
    path('dashboard/b2c/', B2CDashboardView.as_view(), name='kpi-b2c'),
    path('dashboard/course/<int:course_id>/', CourseKPIView.as_view(), name='kpi-course'),
    path('skill-gap/', SkillGapView.as_view(), name='skill-gap-me'),
    path('skill-gap/<int:user_id>/', SkillGapView.as_view(), name='skill-gap-user'),
] + router.urls
