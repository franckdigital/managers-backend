from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.constants import Roles
from apps.core.permissions import HasRole
from apps.kpi_pro.catalog import (
    EMPLOYEE_CATEGORIES,
    EMPLOYEE_KPI_DESCRIPTIONS,
    RATABLE_TRAINER_KPIS,
    TRAINER_CATEGORIES,
    TRAINER_KPI_DESCRIPTIONS,
    build_kpi_rows,
)
from apps.kpi_pro.engine_dashboard import (
    ai_risk_scatter,
    compute_nine_box,
    consolidated_dashboard,
    department_heatmap,
    soft_skills_by_group,
)
from apps.kpi_pro.engine_employee import compute_employee_kpis, employee_content_breakdown, lpi_decomposition
from apps.kpi_pro.engine_skills import skill_comparator
from apps.kpi_pro.engine_trainer import compute_trainer_kpis, tpi_decomposition
from apps.kpi_pro.models import TrainerRating
from apps.kpi_pro.serializers import TrainerRatingSerializer

IsHRorAdmin = HasRole.for_roles(Roles.HR, Roles.COMPANY_ADMIN, Roles.TRAINING_CENTER_ADMIN)
_LEARNER_ROLES = {Roles.EMPLOYEE, Roles.MANAGER, Roles.STUDENT}


def _is_hr_admin(user):
    return user.is_superuser or user.role in (Roles.SUPER_ADMIN, Roles.HR, Roles.COMPANY_ADMIN, Roles.TRAINING_CENTER_ADMIN)


def _resolve_company(request):
    """Resolve the company to report on, honouring ?company=<id> drill-down for super admins
    and subsidiary drill-down for company admins/HR (must stay within their company tree)."""
    from apps.tenants.models import Company

    user = request.user
    company_param = request.query_params.get('company')

    if user.is_superuser or user.role == Roles.SUPER_ADMIN:
        if not company_param:
            return None
        try:
            return Company.objects.get(pk=company_param)
        except Company.DoesNotExist:
            return None

    if user.company_id is None:
        return None
    if company_param:
        try:
            requested_id = int(company_param)
        except (ValueError, TypeError):
            requested_id = None
        if requested_id is not None and requested_id in user.company.get_descendant_ids():
            return Company.objects.get(id=requested_id)
    return user.company


class EmployeeKPIView(APIView):
    """GET /api/kpi-pro/employees/ — 100 KPI employés, scope: company (+filiales) / département / employé."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.accounts.models import User

        user = request.user

        if user.role == Roles.MANAGER:
            team_ids = list(User.objects.filter(manager=user, role__in=_LEARNER_ROLES).values_list('id', flat=True))
            scope_label = 'Mon équipe'
            user_ids = team_ids
        elif _is_hr_admin(user):
            company = _resolve_company(request)
            if company is None:
                return Response({'detail': 'Sélectionnez une entreprise.'}, status=400)
            company_ids = company.get_descendant_ids()
            qs = User.objects.filter(company_id__in=company_ids, role__in=_LEARNER_ROLES)

            department_id = request.query_params.get('department')
            if department_id:
                qs = qs.filter(department_id=department_id)

            single_user_id = request.query_params.get('user')
            if single_user_id:
                qs = qs.filter(id=single_user_id)

            user_ids = list(qs.values_list('id', flat=True))
            scope_label = company.name
        else:
            return Response({'detail': 'Accès non autorisé.'}, status=403)

        values = compute_employee_kpis(user_ids)
        categories = build_kpi_rows(EMPLOYEE_CATEGORIES, values, EMPLOYEE_KPI_DESCRIPTIONS)
        return Response({
            'scope': scope_label,
            'headcount': len(user_ids),
            'categories': categories,
            'values': values,
            'lpi': {'score': values.get('lpi_index', 0), 'decomposition': lpi_decomposition(values)},
        })


def _can_view_employee(requester, target):
    return (
        target.id == requester.id
        or _is_hr_admin(requester)
        or (requester.role == Roles.MANAGER and target.manager_id == requester.id)
    )


class EmployeeKPIDetailView(APIView):
    """GET /api/kpi-pro/employees/<user_id>/ — les 100 KPI pour un seul employé (fiche individuelle)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id):
        from apps.accounts.models import User

        target = User.objects.get(pk=user_id)
        if not _can_view_employee(request.user, target):
            return Response({'detail': 'Non autorisé.'}, status=403)

        values = compute_employee_kpis([target.id])
        categories = build_kpi_rows(EMPLOYEE_CATEGORIES, values, EMPLOYEE_KPI_DESCRIPTIONS)
        return Response({
            'scope': target.get_full_name() or target.email,
            'headcount': 1,
            'categories': categories,
            'values': values,
            'lpi': {'score': values.get('lpi_index', 0), 'decomposition': lpi_decomposition(values)},
        })


class EmployeeContentDetailView(APIView):
    """GET /api/kpi-pro/employees/<user_id>/content/ — le détail concret (cours, formations,
    leçons) derrière les KPI de la fiche individuelle, pour une lecture explicable des scores."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id):
        from apps.accounts.models import User

        target = User.objects.get(pk=user_id)
        if not _can_view_employee(request.user, target):
            return Response({'detail': 'Non autorisé.'}, status=403)

        return Response(employee_content_breakdown(target.id))


class DepartmentHeatmapView(APIView):
    """GET /api/kpi-pro/employees/by-department/ — heatmap de compétences par département (Fig. 6)."""

    permission_classes = [IsHRorAdmin]

    def get(self, request):
        company = _resolve_company(request)
        if company is None:
            return Response({'detail': 'Sélectionnez une entreprise.'}, status=400)
        company_ids = company.get_descendant_ids()
        return Response(department_heatmap(company_ids))


class TrainerKPIView(APIView):
    """GET /api/kpi-pro/trainers/ — 50 KPI formateurs + TPI. Scope: entreprise (tous formateurs) ou un formateur."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.accounts.models import User

        user = request.user

        if user.role == Roles.TRAINER:
            trainer_ids = [user.id]
            scope_label = user.get_full_name() or user.email
        elif _is_hr_admin(user):
            company = _resolve_company(request)
            if company is None:
                return Response({'detail': 'Sélectionnez une entreprise.'}, status=400)
            company_ids = company.get_descendant_ids()
            qs = User.objects.filter(company_id__in=company_ids, role=Roles.TRAINER)

            trainer_id = request.query_params.get('trainer')
            if trainer_id:
                qs = qs.filter(id=trainer_id)

            trainer_ids = list(qs.values_list('id', flat=True))
            scope_label = company.name
        else:
            return Response({'detail': 'Accès non autorisé.'}, status=403)

        if not trainer_ids:
            values = {}
            categories = build_kpi_rows(TRAINER_CATEGORIES, {}, TRAINER_KPI_DESCRIPTIONS)
        else:
            values = compute_trainer_kpis(trainer_ids)
            categories = build_kpi_rows(TRAINER_CATEGORIES, values, TRAINER_KPI_DESCRIPTIONS)

        return Response({
            'scope': scope_label,
            'trainer_count': len(trainer_ids),
            'categories': categories,
            'values': values,
            'tpi': {
                'score': values.get('tpi_score', 0),
                'decomposition': tpi_decomposition(values) if values else [],
            },
        })


class TrainerRankingView(APIView):
    """GET /api/kpi-pro/trainers/ranking/ — classement multi-critères de tous les formateurs d'une entreprise."""

    permission_classes = [IsHRorAdmin]

    def get(self, request):
        from apps.accounts.models import User

        company = _resolve_company(request)
        if company is None:
            return Response({'detail': 'Sélectionnez une entreprise.'}, status=400)
        company_ids = company.get_descendant_ids()
        trainers = User.objects.filter(company_id__in=company_ids, role=Roles.TRAINER)

        rows = []
        for trainer in trainers:
            values = compute_trainer_kpis([trainer.id])
            rows.append({
                'trainer_id': trainer.id,
                'full_name': trainer.get_full_name() or trainer.email,
                'tpi': values.get('tpi_score', 0),
                'satisfaction': values.get('avg_satisfaction', 0),
                'success_rate': values.get('learner_success_rate', 0),
            })
        rows.sort(key=lambda r: r['tpi'], reverse=True)
        return Response(rows)


class DashboardRHView(APIView):
    """GET /api/kpi-pro/dashboard/ — vue consolidée DRH : 9-box talents, budget, KPI transverses."""

    permission_classes = [IsHRorAdmin]

    def get(self, request):
        company = _resolve_company(request)
        if company is None:
            return Response({'detail': 'Sélectionnez une entreprise.'}, status=400)
        return Response(consolidated_dashboard(company, include_subsidiaries=True))


class NineBoxView(APIView):
    """GET /api/kpi-pro/nine-box/ — matrice 9-box seule (pour la vue manager, périmètre équipe)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.accounts.models import User

        user = request.user
        if user.role == Roles.MANAGER:
            user_ids = list(User.objects.filter(manager=user, role__in=_LEARNER_ROLES).values_list('id', flat=True))
        elif _is_hr_admin(user):
            company = _resolve_company(request)
            if company is None:
                return Response({'detail': 'Sélectionnez une entreprise.'}, status=400)
            company_ids = company.get_descendant_ids()
            user_ids = list(User.objects.filter(company_id__in=company_ids, role__in=_LEARNER_ROLES).values_list('id', flat=True))
        else:
            return Response({'detail': 'Accès non autorisé.'}, status=403)

        return Response(compute_nine_box(user_ids))


class EmployeeListView(APIView):
    """GET /api/kpi-pro/employees/list/ — liste légère des employés du périmètre avec
    quelques KPI de tête, pour la table de drilldown (clic -> fiche 100 KPI individuelle)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from django.db.models import Q

        from apps.accounts.models import User
        from apps.hr_analytics.kpi import employee_kpis

        user = request.user
        if user.role == Roles.MANAGER:
            qs = User.objects.filter(manager=user, role__in=_LEARNER_ROLES)
        elif _is_hr_admin(user):
            company = _resolve_company(request)
            if company is None:
                return Response({'detail': 'Sélectionnez une entreprise.'}, status=400)
            qs = User.objects.filter(company_id__in=company.get_descendant_ids(), role__in=_LEARNER_ROLES)
        else:
            return Response({'detail': 'Accès non autorisé.'}, status=403)

        department_id = request.query_params.get('department')
        if department_id:
            qs = qs.filter(department_id=department_id)
        search = request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(email__icontains=search)
            )
        limit = min(int(request.query_params.get('limit', 100) or 100), 500)

        rows = []
        for member in qs.select_related('department')[:limit]:
            k = employee_kpis(member)
            rows.append({
                'id': member.id,
                'full_name': member.get_full_name() or member.email,
                'department': member.department.name if member.department else None,
                'job_title': member.job_title,
                'average_score': k['average_score'],
                'progress_percent': k['progress_percent'],
                'skills_percent': k['skills_percent'],
            })
        return Response({'count': qs.count(), 'results': rows})


class TrainerRatingViewSet(viewsets.ModelViewSet):
    """Notation d'un formateur par un apprenant sur les critères perceptibles (21 des 50 KPI Formateurs)."""

    serializer_class = TrainerRatingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = TrainerRating.objects.select_related('trainer', 'evaluator', 'course')
        if _is_hr_admin(user):
            company = _resolve_company(self.request)
            if company is None:
                return qs.none()
            qs = qs.filter(trainer__company_id__in=company.get_descendant_ids())
            trainer_id = self.request.query_params.get('trainer')
            if trainer_id:
                qs = qs.filter(trainer_id=trainer_id)
            return qs
        if user.role == Roles.TRAINER:
            return qs.filter(trainer=user)
        return qs.filter(evaluator=user)

    def perform_create(self, serializer):
        serializer.save(evaluator=self.request.user)


class RatableTrainerKPIsView(APIView):
    """GET /api/kpi-pro/trainer-ratings/criteria/ — la liste des 21 critères notables par un apprenant."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response([{'key': key, 'label': label} for key, label in RATABLE_TRAINER_KPIS])


class MyTrainersToRateView(APIView):
    """GET /api/kpi-pro/trainer-ratings/my-trainers/ — mes formations (avec formateur assigné)
    à noter, et si une notation existe déjà pour chacune."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.courses.models import Enrollment

        user = request.user
        enrollments = (
            Enrollment.objects.filter(user=user, course__instructor__isnull=False)
            .select_related('course', 'course__instructor')
            .order_by('-created_at')
        )
        rated_pairs = set(
            TrainerRating.objects.filter(evaluator=user).values_list('trainer_id', 'course_id')
        )
        seen = set()
        rows = []
        for enrollment in enrollments:
            course = enrollment.course
            key = (course.instructor_id, course.id)
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                'course_id': course.id,
                'course_title': course.title,
                'trainer_id': course.instructor_id,
                'trainer_name': course.instructor.get_full_name() or course.instructor.email,
                'enrollment_status': enrollment.status,
                'already_rated': key in rated_pairs,
            })
        return Response(rows)


class SkillComparatorView(APIView):
    """GET /api/kpi-pro/skills/comparator/ — Comparateur IA : objectifs de poste vs compétences
    réelles vs écarts à combler, avec recommandations de formation priorisées."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        user_id_param = request.query_params.get('user')

        if user_id_param:
            target_id = int(user_id_param)
            if not (
                target_id == user.id or _is_hr_admin(user)
                or (user.role == Roles.MANAGER)
            ):
                return Response({'detail': 'Non autorisé.'}, status=403)
            return Response(skill_comparator(None, user_id=target_id))

        if user.role in (Roles.EMPLOYEE, Roles.STUDENT, Roles.TRAINER):
            return Response(skill_comparator(None, user_id=user.id))

        company = _resolve_company(request)
        if company is None:
            return Response({'detail': 'Sélectionnez une entreprise.'}, status=400)
        return Response(skill_comparator(company.get_descendant_ids()))


class SoftSkillsGroupView(APIView):
    """GET /api/kpi-pro/employees/soft-skills-groups/ — Radar comparatif Direction vs Opérationnel (Fig. 9)."""

    permission_classes = [IsHRorAdmin]

    def get(self, request):
        company = _resolve_company(request)
        if company is None:
            return Response({'detail': 'Sélectionnez une entreprise.'}, status=400)
        return Response(soft_skills_by_group(company.get_descendant_ids()))


class AIRiskScatterView(APIView):
    """GET /api/kpi-pro/employees/risk-scatter/ — nuage de points prédiction IA (Fig. 11)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.accounts.models import User

        user = request.user
        if user.role == Roles.MANAGER:
            user_ids = list(User.objects.filter(manager=user, role__in=_LEARNER_ROLES).values_list('id', flat=True))
        elif _is_hr_admin(user):
            company = _resolve_company(request)
            if company is None:
                return Response({'detail': 'Sélectionnez une entreprise.'}, status=400)
            user_ids = list(
                User.objects.filter(company_id__in=company.get_descendant_ids(), role__in=_LEARNER_ROLES)
                .values_list('id', flat=True)
            )
        else:
            return Response({'detail': 'Accès non autorisé.'}, status=403)

        return Response(ai_risk_scatter(user_ids))
