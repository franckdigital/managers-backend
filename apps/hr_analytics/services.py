from django.utils import timezone

from apps.hr_analytics.models import EmployeeSkill


def update_employee_skills_from_course(user, course):
    """Returns the list of (employee_skill, levels_gained) for skills that actually
    progressed, so callers (e.g. gamification) can reward the gain — not just record it."""

    gains = []
    for course_skill in course.skills.select_related('skill'):
        employee_skill, _ = EmployeeSkill.objects.get_or_create(
            user=user, skill=course_skill.skill, defaults={'level': 0}
        )
        if course_skill.level_gained > employee_skill.level:
            levels_gained = course_skill.level_gained - employee_skill.level
            employee_skill.level = course_skill.level_gained
            employee_skill.source = EmployeeSkill.SOURCE_AUTO
            employee_skill.last_assessed_at = timezone.now()
            employee_skill.save(update_fields=['level', 'source', 'last_assessed_at'])
            gains.append((employee_skill, levels_gained))
    return gains
