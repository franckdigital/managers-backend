from datetime import timedelta

from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.core.constants import Roles


def course_kpis(course):
    from apps.assessments.models import AssessmentAttempt
    from apps.courses.models import Enrollment, Lesson
    from apps.progression.models import CourseView, LessonProgress

    enrollments = Enrollment.objects.filter(course=course)
    total = enrollments.count()
    completed = enrollments.filter(status=Enrollment.STATUS_COMPLETED).count()
    dropped = enrollments.filter(status=Enrollment.STATUS_DROPPED).count()
    avg_score = AssessmentAttempt.objects.filter(assessment__course=course, score__isnull=False).aggregate(avg=Avg('score'))['avg'] or 0

    lesson_ids = list(Lesson.objects.filter(chapter__section__course=course).values_list('id', flat=True))
    lp_qs = LessonProgress.objects.filter(lesson_id__in=lesson_ids)
    lp_agg = lp_qs.aggregate(
        total_lesson_opens=Sum('open_count'),
        total_video_plays=Sum('video_play_count'),
        total_time_s=Sum('time_spent_seconds'),
        avg_time_s=Avg('time_spent_seconds'),
        avg_watch=Avg('watch_percent'),
    )
    view_agg = CourseView.objects.filter(course=course).aggregate(
        total_course_opens=Sum('open_count'),
        unique_visitors=Count('id'),
    )

    return {
        'total_enrolled': total,
        'completion_rate': round(completed / total * 100, 2) if total else 0,
        'dropout_rate': round(dropped / total * 100, 2) if total else 0,
        'average_score': round(avg_score, 2),
        'total_certifications': course.certificates.count(),
        # Tracking
        'total_course_page_opens': view_agg['total_course_opens'] or 0,
        'unique_visitors': view_agg['unique_visitors'] or 0,
        'total_lesson_opens': lp_agg['total_lesson_opens'] or 0,
        'total_video_plays': lp_agg['total_video_plays'] or 0,
        'total_time_spent_hours': round((lp_agg['total_time_s'] or 0) / 3600, 2),
        'avg_time_per_learner_minutes': round((lp_agg['avg_time_s'] or 0) / 60, 2),
        'avg_watch_percent': round(float(lp_agg['avg_watch'] or 0), 2),
    }


def employee_kpis(user):
    from apps.assessments.models import AssessmentAttempt
    from apps.certificates.models import Certificate
    from apps.courses.models import Enrollment
    from apps.hr_analytics.models import EmployeeSkill, PDIObjective
    from apps.progression.models import CourseView, LessonProgress
    from apps.virtual_classes.models import VirtualClassAttendance

    enrollments = Enrollment.objects.filter(user=user)
    total_courses = enrollments.count()
    completed_courses = enrollments.filter(status=Enrollment.STATUS_COMPLETED).count()
    avg_progress = enrollments.aggregate(avg=Avg('progress_percent'))['avg'] or 0
    avg_score = AssessmentAttempt.objects.filter(user=user, score__isnull=False).aggregate(avg=Avg('score'))['avg'] or 0

    skills = EmployeeSkill.objects.filter(user=user)
    avg_skill_level = skills.aggregate(avg=Avg('level'))['avg'] or 0

    lp_agg = LessonProgress.objects.filter(user=user).aggregate(
        total_time_s=Sum('time_spent_seconds'),
        total_lesson_opens=Sum('open_count'),
        total_video_plays=Sum('video_play_count'),
        avg_watch_percent=Avg('watch_percent'),
        watched_s=Sum('watched_seconds'),
    )
    virtual_seconds = VirtualClassAttendance.objects.filter(user=user).aggregate(
        total=Sum('duration_seconds')
    )['total'] or 0

    total_time_seconds = (lp_agg['total_time_s'] or 0) + virtual_seconds
    time_spent_hours = round(total_time_seconds / 3600, 2)
    time_spent_minutes = round(total_time_seconds / 60, 2)

    total_course_opens = CourseView.objects.filter(user=user).aggregate(
        total=Sum('open_count')
    )['total'] or 0

    objectives = PDIObjective.objects.filter(plan__user=user)
    total_objectives = objectives.count()
    achieved_objectives = objectives.filter(status=PDIObjective.STATUS_ACHIEVED).count()

    overdue_count = Enrollment.objects.filter(
        user=user, due_date__lt=timezone.now().date(), status=Enrollment.STATUS_IN_PROGRESS
    ).count()

    return {
        'total_courses_enrolled': total_courses,
        'completed_courses': completed_courses,
        'progress_percent': round(avg_progress, 2),
        'average_score': round(avg_score, 2),
        'skills_percent': round(avg_skill_level / 5 * 100, 2),
        'attendance_hours': time_spent_hours,
        'time_spent_hours': time_spent_hours,
        'time_spent_minutes': time_spent_minutes,
        # Tracking interactions
        'total_course_page_opens': total_course_opens,
        'total_lesson_opens': lp_agg['total_lesson_opens'] or 0,
        'total_video_plays': lp_agg['total_video_plays'] or 0,
        'avg_watch_percent': round(float(lp_agg['avg_watch_percent'] or 0), 2),
        # Certifications & objectifs
        'certifications_count': Certificate.objects.filter(user=user, is_revoked=False).count(),
        'objectives_achieved_percent': round(achieved_objectives / total_objectives * 100, 2) if total_objectives else 0,
        'overdue_count': overdue_count,
    }


def manager_team_kpis(manager):
    from apps.accounts.models import User
    from apps.courses.models import Enrollment

    team = User.objects.filter(manager=manager)
    rows = []
    for member in team:
        kpis = employee_kpis(member)
        kpis['user_id'] = member.id
        kpis['full_name'] = member.get_full_name()
        rows.append(kpis)

    at_risk = [row for row in rows if row['progress_percent'] < 30]
    top_performers = sorted(rows, key=lambda r: r['average_score'], reverse=True)[:5]
    late = Enrollment.objects.filter(
        user__manager=manager, due_date__lt=timezone.now().date(), status=Enrollment.STATUS_IN_PROGRESS
    ).select_related('user', 'course')

    return {
        'team_size': team.count(),
        'members': rows,
        'top_performers': top_performers,
        'at_risk_of_dropout': at_risk,
        'overdue_enrollments': [
            {'user': e.user.get_full_name(), 'course': e.course.title, 'due_date': e.due_date} for e in late
        ],
    }


_LEARNER_ROLES = None

def _get_learner_roles():
    global _LEARNER_ROLES
    if _LEARNER_ROLES is None:
        _LEARNER_ROLES = {Roles.EMPLOYEE, Roles.MANAGER, Roles.STUDENT}
    return _LEARNER_ROLES


def hr_team_kpis_for_company(company):
    """KPIs pour tous les employés d'une company donnée — sous-fonction réutilisable."""
    from apps.accounts.models import User
    from apps.courses.models import Enrollment
    from apps.hr_analytics.models import Evaluation360Response

    learner_roles = _get_learner_roles()
    team = User.objects.filter(
        company_id=company.id,
        role__in=learner_roles,
    ).select_related('department', 'manager')

    rows = []
    for member in team:
        kpis = employee_kpis(member)
        kpis['user_id'] = member.id
        kpis['full_name'] = member.get_full_name() or member.email
        kpis['department'] = member.department.name if member.department else None
        kpis['job_title'] = member.job_title
        kpis['role'] = member.role
        kpis['manager_name'] = member.manager.get_full_name() if member.manager else None
        final_eval = (
            Evaluation360Response.objects
            .filter(campaign__target_user=member, evaluator_type='final', overall_score__isnull=False)
            .order_by('-submitted_at')
            .values_list('overall_score', flat=True)
            .first()
        )
        kpis['auto_eval_score'] = float(final_eval) if final_eval is not None else None
        rows.append(kpis)

    at_risk = [row for row in rows if row['progress_percent'] < 30]
    top_performers = sorted(rows, key=lambda r: (r['average_score'], r['progress_percent']), reverse=True)[:10]
    late = Enrollment.objects.filter(
        user__company_id=company.id,
        due_date__lt=timezone.now().date(),
        status=Enrollment.STATUS_IN_PROGRESS,
    ).select_related('user', 'course')

    return {
        'team_size': team.count(),
        'members': rows,
        'top_performers': top_performers,
        'at_risk_of_dropout': at_risk,
        'overdue_enrollments': [
            {'user': e.user.get_full_name(), 'course': e.course.title, 'due_date': e.due_date} for e in late
        ],
    }


def hr_team_kpis(requesting_user):
    """KPIs pour tous les employés de l'entreprise — vue RH/Admin."""
    from apps.tenants.models import Company
    company = Company.objects.get(pk=requesting_user.company_id)
    return hr_team_kpis_for_company(company)


def skill_gap_analysis(user, job_role_id=None):
    """Compare an employee's skill levels against a job role's requirements.
    Returns a list of role-gap objects — one per matched job role."""
    from apps.hr_analytics.models import EmployeeSkill, JobRole

    user_skills = {es.skill_id: es.level for es in EmployeeSkill.objects.filter(user=user).select_related('skill')}

    roles_qs = JobRole.objects.prefetch_related('skill_requirements__skill')
    if job_role_id:
        roles_qs = roles_qs.filter(pk=job_role_id)
    elif user.company_id:
        roles_qs = roles_qs.filter(company_id=user.company_id)
    else:
        return []

    result = []
    for role in roles_qs:
        gaps = []
        for req in role.skill_requirements.all():
            actual = user_skills.get(req.skill_id, 0)
            gaps.append({
                'skill_id': req.skill_id,
                'skill_name': req.skill.name,
                'required_level': req.required_level,
                'actual_level': actual,
                'gap': max(0, req.required_level - actual),
            })
        total_required = sum(g['required_level'] for g in gaps)
        total_actual = sum(min(g['actual_level'], g['required_level']) for g in gaps)
        result.append({
            'job_role_id': role.id,
            'job_role_title': role.title,
            'skills': gaps,
            'coverage_percent': round(total_actual / total_required * 100, 2) if total_required else 100,
            'gap_percent': round((1 - total_actual / total_required) * 100, 2) if total_required else 0,
        })
    return result


def company_hr_dashboard(company, include_subsidiaries=True):
    from apps.accounts.models import User
    from apps.assessments.models import AssessmentAttempt
    from apps.certificates.models import Certificate
    from apps.courses.models import Course, Enrollment
    from apps.hr_analytics.models import TrainingBudgetEntry
    from apps.tenants.models import Department
    from django.db.models.functions import TruncMonth

    company_ids = company.get_descendant_ids() if include_subsidiaries else {company.id}
    learner_roles = _get_learner_roles()

    employees = User.objects.filter(company_id__in=company_ids, role__in=learner_roles)
    total_employees = employees.count()
    enrollments = Enrollment.objects.filter(user__company_id__in=company_ids, user__role__in=learner_roles)
    total_enrollments = enrollments.count()
    # Count distinct courses enrolled by learners (company-owned + B2C courses they follow)
    total_distinct_courses = enrollments.values('course').distinct().count()
    courses = Course.objects.filter(company_id__in=company_ids)

    enrolled_employees = enrollments.values('user').distinct().count()
    completed_enrollments = enrollments.filter(status=Enrollment.STATUS_COMPLETED).count()
    dropped_enrollments = enrollments.filter(status=Enrollment.STATUS_DROPPED).count()
    overdue_count = Enrollment.objects.filter(
        user__company_id__in=company_ids,
        user__role__in=learner_roles,
        due_date__lt=timezone.now().date(),
        status=Enrollment.STATUS_IN_PROGRESS,
    ).count()
    avg_score = AssessmentAttempt.objects.filter(
        user__company_id__in=company_ids,
        user__role__in=learner_roles,
        score__isnull=False,
    ).aggregate(avg=Avg('score'))['avg'] or 0

    by_department = []
    for department in Department.objects.filter(company_id__in=company_ids).select_related('company'):
        dept_employees = employees.filter(department=department)  # already filtered to learner_roles
        dept_enrollments = enrollments.filter(user__department=department)
        avg_progress = dept_enrollments.aggregate(avg=Avg('progress_percent'))['avg'] or 0
        label = department.name if len(company_ids) == 1 else f'{department.name} ({department.company.name})'
        by_department.append({
            'department': label,
            'employees': dept_employees.count(),
            'average_progress': round(avg_progress, 2),
        })

    budgets = TrainingBudgetEntry.objects.filter(company_id__in=company_ids, year=timezone.now().year)
    amount_allocated = budgets.aggregate(total=Sum('amount_allocated'))['total'] or 0
    amount_spent = budgets.aggregate(total=Sum('amount_spent'))['total'] or 0
    total_training_hours = sum(c.total_duration_minutes for c in courses) / 60
    trained_employees = (
        enrollments.filter(status=Enrollment.STATUS_COMPLETED).values('user').distinct().count()
        if completed_enrollments else 0
    )

    roi = None
    cost_per_employee = None
    if amount_spent and total_employees:
        cost_per_employee = round(float(amount_spent) / total_employees, 2)
        # ROI formula: effectiveness-adjusted return
        # effectiveness = completion_rate × avg_score / 100
        # A 100%-effective programme is assumed to return 3× the investment
        if total_enrollments:
            effectiveness = (completed_enrollments / total_enrollments) * (float(avg_score) / 100)
        else:
            effectiveness = 0
        estimated_benefit = float(amount_spent) * effectiveness * 3
        roi = round((estimated_benefit - float(amount_spent)) / float(amount_spent) * 100, 2)

    one_year_ago = timezone.now() - timedelta(days=365)
    monthly_trend = (
        Enrollment.objects.filter(
            user__company_id__in=company_ids,
            status=Enrollment.STATUS_COMPLETED,
            completed_at__gte=one_year_ago,
        )
        .annotate(month=TruncMonth('completed_at'))
        .values('month')
        .order_by('month')
        .annotate(completions=Count('id'))
    )

    return {
        'total_employees': total_employees,
        'total_courses': total_distinct_courses,
        'enrollment_rate': round(enrolled_employees / total_employees * 100, 2) if total_employees else 0,
        'participation_rate': round(enrolled_employees / total_employees * 100, 2) if total_employees else 0,
        'global_completion_rate': round(completed_enrollments / total_enrollments * 100, 2) if total_enrollments else 0,
        'global_dropout_rate': round(dropped_enrollments / total_enrollments * 100, 2) if total_enrollments else 0,
        'global_average_score': round(avg_score, 2),
        'overdue_count': overdue_count,
        'total_certifications': Certificate.objects.filter(
            user__company_id__in=company_ids, is_revoked=False
        ).count(),
        'competencies_by_department': by_department,
        'training_hours': round(total_training_hours, 2),
        'budget_allocated': amount_allocated,
        'budget_spent': amount_spent,
        'cost_per_employee': cost_per_employee,
        'roi_percent': roi,
        'monthly_completion_trend': [
            {'month': row['month'].strftime('%Y-%m'), 'completions': row['completions']}
            for row in monthly_trend
        ],
    }


def executive_dashboard(company, include_subsidiaries=True):
    """§9 — vue stratégique exécutive (DG): synthèse globale de la formation à
    l'échelle de l'entreprise (et de ses filiales), au-delà du détail opérationnel du tableau RH."""

    from apps.accounts.models import User
    from apps.certificates.models import Certificate
    from apps.courses.models import Enrollment

    company_ids = company.get_descendant_ids() if include_subsidiaries else {company.id}
    base = company_hr_dashboard(company, include_subsidiaries=include_subsidiaries)

    employees = User.objects.filter(company_id__in=company_ids, role__in=_get_learner_roles())
    rows = []
    for member in employees:
        member_kpis = employee_kpis(member)
        member_kpis['user_id'] = member.id
        member_kpis['full_name'] = member.get_full_name()
        member_kpis['department'] = member.department.name if member.department else None
        rows.append(member_kpis)

    top_talents = sorted(rows, key=lambda row: (row['average_score'], row['progress_percent']), reverse=True)[:10]
    at_risk_employees = [
        row for row in rows if row['progress_percent'] < 30 or row['objectives_achieved_percent'] < 30
    ]

    one_year_ago = timezone.now() - timedelta(days=365)
    monthly_trend = (
        Enrollment.objects.filter(
            user__company_id__in=company_ids, status=Enrollment.STATUS_COMPLETED, completed_at__gte=one_year_ago
        )
        .annotate(month=TruncMonth('completed_at'))
        .values('month')
        .order_by('month')
        .annotate(completions=Count('id'))
    )

    return {
        **base,
        'top_talents': top_talents,
        'at_risk_employees': at_risk_employees,
        'monthly_completion_trend': [
            {'month': row['month'].strftime('%Y-%m'), 'completions': row['completions']} for row in monthly_trend
        ],
        'certifications_last_12_months': Certificate.objects.filter(
            user__company_id__in=company_ids, issued_at__gte=one_year_ago, is_revoked=False
        ).count(),
    }


def b2c_aggregate_kpis():
    """Aggregate KPIs for all B2C learners (company=null, role=student)."""
    from apps.accounts.models import User
    from apps.assessments.models import AssessmentAttempt
    from apps.certificates.models import Certificate
    from apps.core.constants import Roles
    from apps.courses.models import Enrollment
    from apps.hr_analytics.models import EmployeeSkill, PDIObjective
    from apps.virtual_classes.models import VirtualClassAttendance

    learners_qs = User.objects.filter(company__isnull=True, role=Roles.STUDENT)
    total_learners = learners_qs.count()
    active_learners = learners_qs.filter(is_active=True).count()

    one_month_ago = timezone.now() - timedelta(days=30)
    new_this_month = learners_qs.filter(date_joined__gte=one_month_ago).count()

    learner_ids = list(learners_qs.values_list('id', flat=True))

    enroll_agg = Enrollment.objects.filter(user_id__in=learner_ids).aggregate(
        total=Count('id'),
        completed=Count('id', filter=Q(status=Enrollment.STATUS_COMPLETED)),
        dropped=Count('id', filter=Q(status=Enrollment.STATUS_DROPPED)),
        avg_progress=Avg('progress_percent'),
    )
    total_enrollments = enroll_agg['total'] or 0
    completed_enrollments = enroll_agg['completed'] or 0
    dropped_enrollments = enroll_agg['dropped'] or 0
    avg_progress = round(enroll_agg['avg_progress'] or 0, 2)

    avg_score = AssessmentAttempt.objects.filter(
        user_id__in=learner_ids, score__isnull=False,
    ).aggregate(avg=Avg('score'))['avg'] or 0

    avg_skill_level = EmployeeSkill.objects.filter(
        user_id__in=learner_ids,
    ).aggregate(avg=Avg('level'))['avg'] or 0

    from apps.progression.models import LessonProgress

    virtual_seconds = VirtualClassAttendance.objects.filter(
        user_id__in=learner_ids,
    ).aggregate(total=Sum('duration_seconds'))['total'] or 0
    lesson_seconds = LessonProgress.objects.filter(
        user_id__in=learner_ids,
    ).aggregate(total=Sum('watched_seconds'))['total'] or 0
    attendance_hours = round((virtual_seconds + lesson_seconds) / 3600, 2)

    total_certifications = Certificate.objects.filter(
        user_id__in=learner_ids, is_revoked=False,
    ).count()

    total_objectives = PDIObjective.objects.filter(plan__user_id__in=learner_ids).count()
    achieved_objectives = PDIObjective.objects.filter(
        plan__user_id__in=learner_ids, status=PDIObjective.STATUS_ACHIEVED,
    ).count()

    overdue_count = Enrollment.objects.filter(
        user_id__in=learner_ids,
        due_date__lt=timezone.now().date(),
        status=Enrollment.STATUS_IN_PROGRESS,
    ).count()

    # Top 5 performers by average score
    top_rows = []
    for learner in learners_qs.filter(is_active=True)[:20]:
        kpis = employee_kpis(learner)
        kpis['user_id'] = learner.id
        kpis['full_name'] = learner.get_full_name() or learner.email
        kpis['country'] = learner.country or ''
        top_rows.append(kpis)
    top_performers = sorted(top_rows, key=lambda r: r['average_score'], reverse=True)[:5]
    at_risk = [r for r in top_rows if r['progress_percent'] < 30]

    one_year_ago = timezone.now() - timedelta(days=365)
    monthly_trend = (
        Enrollment.objects.filter(
            user_id__in=learner_ids,
            status=Enrollment.STATUS_COMPLETED,
            completed_at__gte=one_year_ago,
        )
        .annotate(month=TruncMonth('completed_at'))
        .values('month')
        .order_by('month')
        .annotate(completions=Count('id'))
    )

    return {
        'total_learners': total_learners,
        'active_learners': active_learners,
        'new_this_month': new_this_month,
        'total_enrollments': total_enrollments,
        'completion_rate': round(completed_enrollments / total_enrollments * 100, 2) if total_enrollments else 0,
        'dropout_rate': round(dropped_enrollments / total_enrollments * 100, 2) if total_enrollments else 0,
        'progress_percent': avg_progress,
        'average_score': round(float(avg_score), 2),
        'skills_percent': round(float(avg_skill_level) / 5 * 100, 2),
        'attendance_hours': attendance_hours,
        'certifications_count': total_certifications,
        'objectives_achieved_percent': round(achieved_objectives / total_objectives * 100, 2) if total_objectives else 0,
        'overdue_count': overdue_count,
        'top_performers': top_performers,
        'at_risk': at_risk,
        'monthly_completion_trend': [
            {'month': row['month'].strftime('%Y-%m'), 'completions': row['completions']}
            for row in monthly_trend
        ],
    }
