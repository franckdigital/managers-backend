from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.kpi_pro.views import (
    AIRiskScatterView,
    DashboardRHView,
    DepartmentHeatmapView,
    EmployeeContentDetailView,
    EmployeeKPIDetailView,
    EmployeeKPIView,
    EmployeeListView,
    MyTrainersToRateView,
    NineBoxView,
    RatableTrainerKPIsView,
    SkillComparatorView,
    SoftSkillsGroupView,
    TrainerKPIView,
    TrainerRankingView,
    TrainerRatingViewSet,
)

router = DefaultRouter()
router.register('trainer-ratings', TrainerRatingViewSet, basename='trainer-rating')

urlpatterns = [
    path('employees/', EmployeeKPIView.as_view(), name='kpi-pro-employees'),
    path('employees/list/', EmployeeListView.as_view(), name='kpi-pro-employees-list'),
    path('employees/by-department/', DepartmentHeatmapView.as_view(), name='kpi-pro-employees-by-department'),
    path('employees/soft-skills-groups/', SoftSkillsGroupView.as_view(), name='kpi-pro-soft-skills-groups'),
    path('employees/risk-scatter/', AIRiskScatterView.as_view(), name='kpi-pro-risk-scatter'),
    path('employees/<int:user_id>/', EmployeeKPIDetailView.as_view(), name='kpi-pro-employee-detail'),
    path('employees/<int:user_id>/content/', EmployeeContentDetailView.as_view(), name='kpi-pro-employee-content'),
    path('trainers/', TrainerKPIView.as_view(), name='kpi-pro-trainers'),
    path('trainers/ranking/', TrainerRankingView.as_view(), name='kpi-pro-trainers-ranking'),
    path('trainer-ratings/criteria/', RatableTrainerKPIsView.as_view(), name='kpi-pro-trainer-ratings-criteria'),
    path('trainer-ratings/my-trainers/', MyTrainersToRateView.as_view(), name='kpi-pro-my-trainers'),
    path('skills/comparator/', SkillComparatorView.as_view(), name='kpi-pro-skills-comparator'),
    path('dashboard/', DashboardRHView.as_view(), name='kpi-pro-dashboard'),
    path('nine-box/', NineBoxView.as_view(), name='kpi-pro-nine-box'),
] + router.urls
