from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='courses.Enrollment')
def compute_skills_on_completion(sender, instance, created, **kwargs):
    """When an enrollment reaches 'completed', automatically update the
    employee's skill levels based on CourseSkill definitions. Only raises
    the level — never lowers it. Only overwrites non-manager assessments."""
    if instance.status != 'completed':
        return

    try:
        from apps.hr_analytics.models import CourseSkill, EmployeeSkill
    except ImportError:
        return

    for cs in CourseSkill.objects.filter(course=instance.course).select_related('skill'):
        es, _created = EmployeeSkill.objects.get_or_create(
            user=instance.user,
            skill=cs.skill,
            defaults={'level': cs.level_gained, 'source': EmployeeSkill.SOURCE_AUTO},
        )
        if not _created and es.source != EmployeeSkill.SOURCE_MANAGER and es.level < cs.level_gained:
            es.level = cs.level_gained
            es.source = EmployeeSkill.SOURCE_AUTO
            es.save(update_fields=['level', 'source', 'last_assessed_at'])
