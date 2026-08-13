"""Dashboard RH consolidé — Matrice 9-Box Talents, répartition budgétaire et KPI transverses.

Réutilise `apps.hr_analytics.kpi.company_hr_dashboard` pour les agrégats globaux déjà
calculés (budget, ROI, certifications, décrochage) et y ajoute la cartographie des talents
et la répartition budgétaire par poste de dépense.
"""
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from apps.kpi_pro.catalog import BUDGET_BREAKDOWN_SHARES


def _pct(numerator, denominator, ndigits=1):
    if not denominator:
        return 0.0
    return round(numerator / denominator * 100, ndigits)


def _quadrant(perf, potential):
    perf_band = 'faible' if perf < 33 else 'moyen' if perf < 66 else 'eleve'
    pot_band = 'faible' if potential < 33 else 'moyen' if potential < 66 else 'eleve'
    labels = {
        ('faible', 'faible'): 'Sous-performant',
        ('moyen', 'faible'): 'A surveiller',
        ('eleve', 'faible'): 'Performant stable',
        ('faible', 'moyen'): 'A developper',
        ('moyen', 'moyen'): 'Employe cle',
        ('eleve', 'moyen'): 'Haute Performance',
        ('faible', 'eleve'): 'Diamant brut',
        ('moyen', 'eleve'): 'Futur Leader',
        ('eleve', 'eleve'): 'Top Talent',
    }
    return labels[(perf_band, pot_band)]


def compute_nine_box(user_ids):
    """Positionnement Performance x Potentiel pour chaque collaborateur du périmètre."""
    from apps.accounts.models import User
    from apps.assessments.models import AssessmentAttempt
    from apps.courses.models import Enrollment
    from apps.hr_analytics.models import EmployeeSkill, Evaluation360Response

    user_ids = list(user_ids)

    scores_by_user = {
        row['user_id']: float(row['avg'] or 0)
        for row in AssessmentAttempt.objects.filter(user_id__in=user_ids, score__isnull=False)
        .values('user_id').annotate(avg=Avg('score'))
    }
    enroll_by_user = {
        row['user_id']: _pct(row['completed'], row['total'])
        for row in Enrollment.objects.filter(user_id__in=user_ids)
        .values('user_id')
        .annotate(total=Count('id'), completed=Count('id', filter=Q(status=Enrollment.STATUS_COMPLETED)))
    }
    skill_by_user = {
        row['user_id']: float(row['avg'] or 0) / 5 * 100
        for row in EmployeeSkill.objects.filter(user_id__in=user_ids).values('user_id').annotate(avg=Avg('level'))
    }
    eval_by_user = {
        row['campaign__target_user_id']: float(row['avg'] or 0)
        for row in Evaluation360Response.objects.filter(
            campaign__target_user_id__in=user_ids, overall_score__isnull=False
        ).values('campaign__target_user_id').annotate(avg=Avg('overall_score'))
    }

    users = User.objects.filter(id__in=user_ids).only('id', 'first_name', 'last_name', 'email', 'department_id')
    points = []
    for user in users:
        perf = round((scores_by_user.get(user.id, 0) + enroll_by_user.get(user.id, 0)) / 2, 1)
        potential = round((skill_by_user.get(user.id, 0) + eval_by_user.get(user.id, perf)) / 2, 1)
        points.append({
            'user_id': user.id,
            'full_name': user.get_full_name() or user.email,
            'performance': perf,
            'potential': potential,
            'quadrant': _quadrant(perf, potential),
        })
    return points


def budget_breakdown(company_ids):
    from apps.hr_analytics.models import TrainingBudgetEntry

    year = timezone.now().year
    agg = TrainingBudgetEntry.objects.filter(company_id__in=company_ids, year=year).aggregate(
        allocated=Sum('amount_allocated'),
        spent=Sum('amount_spent'),
    )
    allocated = float(agg['allocated'] or 0)
    spent = float(agg['spent'] or 0)
    return {
        'year': year,
        'allocated': allocated,
        'spent': spent,
        'remaining': round(allocated - spent, 2),
        'remaining_percent': round((allocated - spent) / allocated * 100, 1) if allocated else 0,
        'breakdown': [
            {'label': label, 'share_percent': round(share * 100, 1), 'amount': round(spent * share, 2)}
            for label, share in BUDGET_BREAKDOWN_SHARES
        ],
    }


def soft_skills_by_group(company_ids):
    """Comparaison des soft skills (catégorie G) entre managers et équipes opérationnelles (Fig. 9)."""
    from apps.accounts.models import User
    from apps.core.constants import Roles
    from apps.kpi_pro.engine_employee import compute_employee_kpis

    soft_keys = [
        'leadership', 'communication', 'teamwork', 'adaptability', 'time_management',
        'stress_management', 'creativity', 'initiative', 'decision_making', 'emotional_intelligence',
    ]
    dims = [
        'Leadership', 'Communication', "Travail d'équipe", 'Adaptabilité', 'Gestion du temps',
        'Gestion du stress', 'Créativité', 'Initiative', 'Prise de décision', 'Intelligence émotionnelle',
    ]

    management_ids = list(User.objects.filter(company_id__in=company_ids, role=Roles.MANAGER).values_list('id', flat=True))
    operational_ids = list(User.objects.filter(company_id__in=company_ids, role=Roles.EMPLOYEE).values_list('id', flat=True))

    mgmt_vals = compute_employee_kpis(management_ids) if management_ids else {}
    ops_vals = compute_employee_kpis(operational_ids) if operational_ids else {}

    return {
        'dimensions': dims,
        'management': [mgmt_vals.get(k, 0) for k in soft_keys],
        'operational': [ops_vals.get(k, 0) for k in soft_keys],
        'management_count': len(management_ids),
        'operational_count': len(operational_ids),
    }


def ai_risk_scatter(user_ids):
    """Nuage de points prédiction IA — progression x activité récente, coloré par score de risque (Fig. 11)."""
    from datetime import timedelta

    from django.db.models import Avg, Count
    from django.utils import timezone

    from apps.accounts.models import User
    from apps.courses.models import Enrollment
    from apps.progression.models import LessonProgress

    now = timezone.now()
    d30 = now - timedelta(days=30)

    progress_by_user = {
        row['user_id']: float(row['avg'] or 0)
        for row in Enrollment.objects.filter(user_id__in=user_ids).values('user_id').annotate(avg=Avg('progress_percent'))
    }
    from django.db.models import Sum

    connections_by_user = {
        row['user_id']: row['c'] or 0
        for row in LessonProgress.objects.filter(user_id__in=user_ids, last_opened_at__gte=d30)
        .values('user_id').annotate(c=Sum('open_count'))
    }

    points = []
    for user in User.objects.filter(id__in=user_ids).only('id', 'first_name', 'last_name', 'email', 'last_active_at'):
        progress = round(progress_by_user.get(user.id, 0), 1)
        connections = connections_by_user.get(user.id, 0)
        inactivity_days = (now - user.last_active_at).days if user.last_active_at else 60
        risk = max(0, min(100, round((100 - progress) * 0.5 + min(inactivity_days, 60) / 60 * 100 * 0.5, 1)))
        points.append({
            'user_id': user.id, 'full_name': user.get_full_name() or user.email,
            'progress': progress, 'connections': connections, 'risk_score': risk,
        })
    return points


def department_heatmap(company_ids):
    """Score composite par département — alimente la heatmap de compétences (Fig. 6)."""
    from apps.accounts.models import User
    from apps.core.constants import Roles
    from apps.kpi_pro.engine_employee import compute_employee_kpis
    from apps.tenants.models import Department

    learner_roles = {Roles.EMPLOYEE, Roles.MANAGER, Roles.STUDENT}
    rows = []
    for department in Department.objects.filter(company_id__in=company_ids).select_related('company'):
        user_ids = list(
            User.objects.filter(department=department, role__in=learner_roles).values_list('id', flat=True)
        )
        if not user_ids:
            continue
        values = compute_employee_kpis(user_ids)
        rows.append({
            'department': department.name,
            'company': department.company.name,
            'headcount': len(user_ids),
            'score_moyen': values['avg_global_score'],
            'competences': values['avg_skill_level_pct'],
            'engagement': values['participation_rate'],
            'completion': values['completion_rate'],
            'digital': values['digital_level'],
        })
    return rows


def consolidated_dashboard(company, include_subsidiaries=True):
    from apps.hr_analytics import kpi as hr_kpi

    base = hr_kpi.company_hr_dashboard(company, include_subsidiaries=include_subsidiaries)
    company_ids = company.get_descendant_ids() if include_subsidiaries else {company.id}

    from apps.accounts.models import User
    from apps.certificates.models import Certificate
    from apps.core.constants import Roles

    learner_roles = {Roles.EMPLOYEE, Roles.MANAGER, Roles.STUDENT}
    employees = User.objects.filter(company_id__in=company_ids, role__in=learner_roles)
    user_ids = list(employees.values_list('id', flat=True))
    total_employees = len(user_ids) or 1

    nine_box = compute_nine_box(user_ids)
    talents = [p for p in nine_box if p['quadrant'] in ('Top Talent', 'Futur Leader', 'Diamant brut')]
    at_risk = [p for p in nine_box if p['quadrant'] in ('Sous-performant', 'A surveiller')]

    certified_count = Certificate.objects.filter(user_id__in=user_ids, is_revoked=False).values('user_id').distinct().count()

    budget = budget_breakdown(company_ids)

    avg_perf = round(sum(p['performance'] for p in nine_box) / len(nine_box), 1) if nine_box else 0
    maturity_index = round((avg_perf + _pct(certified_count, total_employees) + base['global_completion_rate']) / 3, 1)

    return {
        **base,
        'nine_box': nine_box,
        'talents_count': len(talents),
        'talents_percent': _pct(len(talents), total_employees),
        'at_risk_count': len(at_risk),
        'certified_employees': certified_count,
        'certified_percent': _pct(certified_count, total_employees),
        'compliance_rate': base.get('global_completion_rate', 0),
        'maturity_index': maturity_index,
        'avg_performance': avg_perf,
        'budget_detail': budget,
    }
