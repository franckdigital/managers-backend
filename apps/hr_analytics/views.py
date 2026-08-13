from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.constants import Roles
from apps.core.mixins import CompanyScopedViewSetMixin
from apps.core.permissions import HasRole, IsCompanyAdmin, IsHR, IsManager
from apps.hr_analytics import kpi
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
from apps.hr_analytics.serializers import (
    CourseSkillSerializer,
    EmployeeSkillSerializer,
    Evaluation360CampaignSerializer,
    Evaluation360ResponseSerializer,
    IndividualDevelopmentPlanSerializer,
    JobRoleSerializer,
    JobRoleSkillRequirementSerializer,
    PDIObjectiveSerializer,
    SkillSerializer,
    TrainingBudgetEntrySerializer,
)

IsHRorAdmin = HasRole.for_roles(Roles.HR, Roles.COMPANY_ADMIN, Roles.TRAINING_CENTER_ADMIN)


class SkillViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [IsHRorAdmin]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'role', None) == Roles.TRAINING_CENTER_ADMIN:
            # TC admin sees platform-wide skills (B2C learner referential)
            return Skill.objects.filter(company__isnull=True)
        return super().get_queryset()


class CourseSkillViewSet(viewsets.ModelViewSet):
    queryset = CourseSkill.objects.select_related('course', 'skill').all()
    serializer_class = CourseSkillSerializer
    permission_classes = [IsHRorAdmin]
    filterset_fields = ['course', 'skill']


class JobRoleViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = JobRole.objects.prefetch_related('skill_requirements__skill').all()
    serializer_class = JobRoleSerializer
    permission_classes = [IsHRorAdmin]


class JobRoleSkillRequirementViewSet(viewsets.ModelViewSet):
    queryset = JobRoleSkillRequirement.objects.select_related('job_role', 'skill').all()
    serializer_class = JobRoleSkillRequirementSerializer
    permission_classes = [IsHRorAdmin]
    filterset_fields = ['job_role']


class EmployeeSkillViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSkillSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['user', 'skill']

    def get_queryset(self):
        user = self.request.user
        qs = EmployeeSkill.objects.select_related('user', 'skill')
        if user.is_superuser or user.role in (Roles.SUPER_ADMIN, Roles.HR, Roles.COMPANY_ADMIN):
            return qs
        if user.role == Roles.TRAINING_CENTER_ADMIN:
            # TC admin sees B2C learner skills
            return qs.filter(user__company__isnull=True, user__role=Roles.STUDENT)
        if user.role == Roles.MANAGER:
            return qs.filter(user__manager=user)
        return qs.filter(user=user)


class IndividualDevelopmentPlanViewSet(viewsets.ModelViewSet):
    serializer_class = IndividualDevelopmentPlanSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['user', 'status']

    def get_queryset(self):
        user = self.request.user
        qs = IndividualDevelopmentPlan.objects.select_related('user').prefetch_related('objectives')
        if user.is_superuser or user.role in (Roles.SUPER_ADMIN, Roles.HR, Roles.COMPANY_ADMIN):
            return qs
        if user.role == Roles.TRAINING_CENTER_ADMIN:
            # TC admin sees and manages B2C learner development plans
            return qs.filter(user__company__isnull=True, user__role=Roles.STUDENT)
        if user.role == Roles.MANAGER:
            return qs.filter(user__manager=user)
        return qs.filter(user=user)

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [HasRole.for_roles(Roles.MANAGER, Roles.HR, Roles.COMPANY_ADMIN, Roles.TRAINING_CENTER_ADMIN)()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class PDIObjectiveViewSet(viewsets.ModelViewSet):
    queryset = PDIObjective.objects.select_related('plan', 'skill', 'course').all()
    serializer_class = PDIObjectiveSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['plan', 'status']


class Evaluation360CampaignViewSet(CompanyScopedViewSetMixin, viewsets.ModelViewSet):
    queryset = Evaluation360Campaign.objects.select_related('target_user').prefetch_related('responses').all()
    serializer_class = Evaluation360CampaignSerializer
    permission_classes = [IsHR]
    filterset_fields = ['target_user', 'status']

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company, created_by=self.request.user)


class Evaluation360ResponseViewSet(viewsets.ModelViewSet):
    queryset = Evaluation360Response.objects.select_related('campaign', 'evaluator').all()
    serializer_class = Evaluation360ResponseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['campaign', 'evaluator_type']

    def perform_create(self, serializer):
        from django.utils import timezone

        serializer.save(evaluator=self.request.user, submitted_at=timezone.now())


class TrainingBudgetEntryViewSet(viewsets.ModelViewSet):
    serializer_class = TrainingBudgetEntrySerializer
    permission_classes = [IsHRorAdmin]
    filterset_fields = ['year']

    def get_queryset(self):
        return TrainingBudgetEntry.objects.filter(company_id=self.request.user.company_id)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class EmployeeKPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id=None):
        from apps.accounts.models import User

        target = request.user if user_id is None else User.objects.get(pk=user_id)
        if target != request.user and not (
            request.user.is_superuser
            or request.user.role in (Roles.SUPER_ADMIN, Roles.HR, Roles.COMPANY_ADMIN)
            or (request.user.role == Roles.TRAINING_CENTER_ADMIN and target.company is None)
            or (request.user.role == Roles.MANAGER and target.manager_id == request.user.id)
        ):
            return Response({'detail': 'Non autorisé.'}, status=403)
        return Response(kpi.employee_kpis(target))


_EMPTY_TEAM = {'team_size': 0, 'members': [], 'top_performers': [], 'at_risk_of_dropout': [], 'overdue_enrollments': []}


class ManagerDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.tenants.models import Company

        user = request.user
        company_param = request.query_params.get('company')

        # Super admin: drill into a specific company via ?company=
        if user.is_superuser or user.role == Roles.SUPER_ADMIN:
            if not company_param:
                return Response(_EMPTY_TEAM)
            try:
                company = Company.objects.get(pk=company_param)
                return Response(kpi.hr_team_kpis_for_company(company))
            except Company.DoesNotExist:
                return Response(_EMPTY_TEAM)

        if user.role in (Roles.COMPANY_ADMIN, Roles.HR):
            if not user.company_id:
                return Response({'detail': 'Aucune entreprise associée.'}, status=400)
            # Optional drill-down to a subsidiary
            if company_param:
                try:
                    requested = int(company_param)
                    if requested in user.company.get_descendant_ids():
                        company = Company.objects.get(pk=requested)
                        return Response(kpi.hr_team_kpis_for_company(company))
                except (ValueError, TypeError):
                    pass
            return Response(kpi.hr_team_kpis(user))

        if user.role == Roles.MANAGER:
            return Response(kpi.manager_team_kpis(user))

        return Response({'detail': 'Accès non autorisé.'}, status=403)


def _resolve_dashboard_company(request):
    """Resolve the company to report on: the user's own company, or a subsidiary requested
    via ?company=<id> for drill-down (rejected if outside the user's company tree)."""
    from apps.tenants.models import Company

    company = request.user.company
    requested = request.query_params.get('company')
    if requested and company is not None:
        try:
            requested_id = int(requested)
        except (TypeError, ValueError):
            return company
        if requested_id in company.get_descendant_ids():
            return Company.objects.get(id=requested_id)
    return company


class HRDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.tenants.models import Company

        user = request.user
        company_param = request.query_params.get('company')

        if user.is_superuser or user.role == Roles.SUPER_ADMIN:
            if not company_param:
                return Response({'detail': 'Sélectionnez une entreprise.'}, status=400)
            try:
                company = Company.objects.get(pk=company_param)
                return Response(kpi.company_hr_dashboard(company, include_subsidiaries=True))
            except Company.DoesNotExist:
                return Response({'detail': 'Entreprise introuvable.'}, status=404)

        if user.role not in (Roles.HR, Roles.COMPANY_ADMIN):
            return Response({'detail': 'Accès non autorisé.'}, status=403)
        if user.company_id is None:
            return Response({'detail': "Aucune entreprise associée à ce compte."}, status=400)
        company = _resolve_dashboard_company(request)
        return Response(kpi.company_hr_dashboard(company, include_subsidiaries=company == user.company))


class HRDashboardExportView(APIView):
    """§18 — Rapports: export CSV du tableau de bord RH (KPIs globaux + détail par département)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        import csv

        from django.http import HttpResponse
        from apps.tenants.models import Company

        user = request.user
        company_param = request.query_params.get('company')

        if user.is_superuser or user.role == Roles.SUPER_ADMIN:
            if not company_param:
                return Response({'detail': 'Sélectionnez une entreprise.'}, status=400)
            try:
                company = Company.objects.get(pk=company_param)
            except Company.DoesNotExist:
                return Response({'detail': 'Entreprise introuvable.'}, status=404)
            data = kpi.company_hr_dashboard(company, include_subsidiaries=True)
        elif user.role in (Roles.HR, Roles.COMPANY_ADMIN):
            if user.company_id is None:
                return Response({'detail': "Aucune entreprise associée à ce compte."}, status=400)
            company = _resolve_dashboard_company(request)
            data = kpi.company_hr_dashboard(company, include_subsidiaries=company == user.company)
        else:
            return Response({'detail': 'Accès non autorisé.'}, status=403)

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="rapport_rh_{company.id}.csv"'
        writer = csv.writer(response)

        writer.writerow(['Rapport RH', company.name])
        writer.writerow([])
        writer.writerow(['Indicateur', 'Valeur'])
        writer.writerow(['Employés', data['total_employees']])
        writer.writerow(['Cours', data['total_courses']])
        writer.writerow(['Taux de complétion global (%)', data['global_completion_rate']])
        writer.writerow(['Taux de décrochage global (%)', data['global_dropout_rate']])
        writer.writerow(['Score moyen global (%)', data['global_average_score']])
        writer.writerow(['Heures de formation', data['training_hours']])
        writer.writerow(['Budget alloué', data['budget_allocated']])
        writer.writerow(['Budget dépensé', data['budget_spent']])
        writer.writerow(['Coût par employé', data['cost_per_employee']])
        writer.writerow(['ROI formation (%)', data['roi_percent']])
        writer.writerow(['Certifications délivrées', data['total_certifications']])
        writer.writerow([])
        writer.writerow(['Département', 'Employés', 'Progression moyenne (%)'])
        for dept in data['competencies_by_department']:
            writer.writerow([dept['department'], dept['employees'], dept['average_progress']])

        return response


class ExecutiveDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.tenants.models import Company

        user = request.user
        company_param = request.query_params.get('company')

        if user.is_superuser or user.role == Roles.SUPER_ADMIN:
            if not company_param:
                return Response({'detail': 'Sélectionnez une entreprise.'}, status=400)
            try:
                company = Company.objects.get(pk=company_param)
                return Response(kpi.executive_dashboard(company, include_subsidiaries=True))
            except Company.DoesNotExist:
                return Response({'detail': 'Entreprise introuvable.'}, status=404)

        if user.role not in (Roles.COMPANY_ADMIN, Roles.HR):
            return Response({'detail': 'Accès non autorisé.'}, status=403)
        if user.company_id is None:
            return Response({'detail': "Aucune entreprise associée à ce compte."}, status=400)
        company = _resolve_dashboard_company(request)
        return Response(kpi.executive_dashboard(company, include_subsidiaries=company == user.company))


class CourseKPIView(APIView):
    permission_classes = [IsHRorAdmin]

    def get(self, request, course_id):
        from apps.courses.models import Course

        course = Course.objects.get(pk=course_id)
        return Response(kpi.course_kpis(course))


class B2CDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not (
            request.user.is_superuser
            or request.user.role in (Roles.SUPER_ADMIN, Roles.TRAINING_CENTER_ADMIN)
        ):
            return Response({'detail': 'Non autorisé.'}, status=403)
        return Response(kpi.b2c_aggregate_kpis())


class SkillGapView(APIView):
    """Return skill gap analysis for the current user (or a specific user for HR/admin)
    vs a given job role (?job_role=<id>) or all job roles in the company."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id=None):
        from apps.accounts.models import User

        if user_id is not None:
            if not (request.user.is_superuser or request.user.role in (Roles.SUPER_ADMIN, Roles.HR, Roles.COMPANY_ADMIN)
                    or (request.user.role == Roles.MANAGER)):
                return Response({'detail': 'Non autorisé.'}, status=403)
            target = User.objects.get(pk=user_id)
        else:
            target = request.user

        job_role_id = request.query_params.get('job_role')
        return Response(kpi.skill_gap_analysis(target, job_role_id=job_role_id))
