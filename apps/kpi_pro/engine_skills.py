"""Comparateur IA Compétences — objectifs de poste vs compétences réelles vs écarts à combler.

Deux modes :
  - `user_id` fourni  -> réutilise `apps.hr_analytics.kpi.skill_gap_analysis` (analyse individuelle,
    une entrée par fiche de poste correspondante).
  - sinon             -> agrège tout le référentiel de compétences requises de l'entreprise face au
    niveau moyen réellement constaté chez les employés du périmètre, et propose une liste de
    priorités de formation (recommandation IA) triée par écart décroissant.
"""


def _avg(values):
    values = [float(v) for v in values if v is not None]
    return round(sum(values) / len(values), 2) if values else 0.0


def skill_comparator(company_ids, user_id=None):
    from apps.accounts.models import User

    if user_id:
        from apps.hr_analytics.kpi import skill_gap_analysis

        target = User.objects.get(pk=user_id)
        role_gaps = skill_gap_analysis(target)
        skills = []
        seen = set()
        for role in role_gaps:
            for s in role['skills']:
                if s['skill_id'] in seen:
                    continue
                seen.add(s['skill_id'])
                required = float(s['required_level']) / 5 * 100
                actual = float(s['actual_level']) / 5 * 100
                skills.append({
                    'skill_id': s['skill_id'], 'skill_name': s['skill_name'],
                    'required_level': round(required, 1), 'actual_level': round(actual, 1),
                    'gap': round(max(0, required - actual), 1),
                    'coverage_percent': round(actual / required * 100, 1) if required else 100,
                    'job_roles': [role['job_role_title']],
                })
        skills.sort(key=lambda r: -r['gap'])
        return _finalize(target.get_full_name() or target.email, skills)

    from apps.core.constants import Roles
    from apps.hr_analytics.models import EmployeeSkill, JobRoleSkillRequirement
    from django.db.models import Avg

    learner_roles = {Roles.EMPLOYEE, Roles.MANAGER, Roles.STUDENT}
    user_ids = list(User.objects.filter(company_id__in=company_ids, role__in=learner_roles).values_list('id', flat=True))

    actual_by_skill = {
        row['skill_id']: float(row['avg'] or 0)
        for row in EmployeeSkill.objects.filter(user_id__in=user_ids).values('skill_id').annotate(avg=Avg('level'))
    }

    reqs = JobRoleSkillRequirement.objects.filter(job_role__company_id__in=company_ids).select_related('skill', 'job_role')
    by_skill = {}
    for req in reqs:
        entry = by_skill.setdefault(req.skill_id, {
            'skill_id': req.skill_id, 'skill_name': req.skill.name,
            'required_level': 0, 'job_roles': set(),
        })
        entry['required_level'] = max(entry['required_level'], req.required_level)
        entry['job_roles'].add(req.job_role.title)

    skills = []
    for entry in by_skill.values():
        required = entry['required_level'] / 5 * 100
        actual = actual_by_skill.get(entry['skill_id'], 0) / 5 * 100
        skills.append({
            'skill_id': entry['skill_id'], 'skill_name': entry['skill_name'],
            'required_level': round(required, 1), 'actual_level': round(actual, 1),
            'gap': round(max(0, required - actual), 1),
            'coverage_percent': round(actual / required * 100, 1) if required else 100,
            'job_roles': sorted(entry['job_roles']),
        })
    skills.sort(key=lambda r: -r['gap'])
    return _finalize('Entreprise (tous postes)', skills)


def _finalize(scope_label, skills):
    from apps.hr_analytics.models import CourseSkill

    priority = [s for s in skills if s['gap'] > 0][:6]
    for s in priority:
        course_skill = CourseSkill.objects.filter(skill_id=s['skill_id']).select_related('course').first()
        s['recommended_course'] = course_skill.course.title if course_skill else None
        if s['gap'] >= 30:
            s['priority'] = 'critical'
        elif s['gap'] >= 15:
            s['priority'] = 'moderate'
        else:
            s['priority'] = 'low'

    return {
        'scope': scope_label,
        'skills': skills,
        'global_coverage': _avg([s['coverage_percent'] for s in skills]) if skills else 100.0,
        'critical_count': len([s for s in skills if s['gap'] >= 30]),
        'priority_recommendations': priority,
    }
