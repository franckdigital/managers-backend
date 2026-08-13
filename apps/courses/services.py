from django.db import transaction
from django.db.models import F

from apps.courses.models import Course, Enrollment


def enroll_user_in_order_courses(order):
    created_enrollments = []
    with transaction.atomic():
        for item in order.items.select_related('course').prefetch_related('bundle__courses'):
            courses = [item.course] if item.course else list(item.bundle.courses.all()) if item.bundle else []
            for course in courses:
                enrollment, created = Enrollment.objects.get_or_create(
                    user=order.user, course=course, defaults={'source': Enrollment.SOURCE_PURCHASE}
                )
                if created:
                    Course.objects.filter(pk=course.pk).update(total_students=F('total_students') + 1)
                    created_enrollments.append(enrollment)
    return created_enrollments


def assign_course(user, course, assigned_by, due_date=None):
    enrollment, created = Enrollment.objects.get_or_create(
        user=user, course=course,
        defaults={'source': Enrollment.SOURCE_ASSIGNED, 'assigned_by': assigned_by, 'due_date': due_date},
    )
    if created:
        Course.objects.filter(pk=course.pk).update(total_students=F('total_students') + 1)
        from apps.notifications.services import notify_user

        notify_user(
            user,
            'Nouvelle formation affectée',
            f"La formation « {course.title} » vous a été affectée"
            + (f" avec une échéance au {due_date}." if due_date else "."),
            data={'course_id': course.id, 'assigned_by': assigned_by.id},
        )
    return enrollment


def recompute_course_rating(course):
    from django.db.models import Avg

    average = course.reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    course.average_rating = round(average, 2)
    course.save(update_fields=['average_rating'])


def commit_scorm_cmi(user, lesson, cmi_patch):
    """Real SCORM RTE persistence: the package's JS API wrapper calls this on every
    LMSCommit/Commit with a partial cmi.* dict; we merge it, derive lesson_status/score/
    suspend_data/session_time, and — on completion/pass — feed the existing progression
    engine via record_lesson_progress so chapter unlock/XP/xAPI all stay consistent."""

    from apps.courses.models import ScormRegistration

    registration, _ = ScormRegistration.objects.get_or_create(user=user, lesson=lesson)
    registration.cmi_data = {**registration.cmi_data, **cmi_patch}

    lesson_status = (
        cmi_patch.get('cmi.core.lesson_status')
        or cmi_patch.get('cmi.completion_status')
        or cmi_patch.get('cmi.success_status')
    )
    if lesson_status:
        registration.lesson_status = lesson_status

    score = cmi_patch.get('cmi.core.score.raw', cmi_patch.get('cmi.score.raw'))
    if score is not None:
        try:
            registration.score_raw = float(score)
        except (TypeError, ValueError):
            pass

    suspend_data = cmi_patch.get('cmi.suspend_data', cmi_patch.get('cmi.core.suspend_data'))
    if suspend_data is not None:
        registration.suspend_data = suspend_data

    session_time = cmi_patch.get('cmi.core.session_time') or cmi_patch.get('cmi.session_time')
    if session_time:
        registration.total_time_seconds += _parse_scorm_session_time(session_time)

    registration.save()

    if registration.lesson_status in ('completed', 'passed'):
        from apps.progression.services import record_lesson_progress

        record_lesson_progress(user, lesson, scorm_completed=True)

    return registration


def _parse_scorm_session_time(value):
    """Parses a SCORM session_time: 1.2 uses HH:MM:SS.ss, 2004 uses ISO 8601 duration (PT1H2M3S)."""

    import re

    if value.startswith('P'):
        match = re.match(r'P(?:\d+D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?', value)
        if not match:
            return 0
        hours, minutes, seconds = (float(group) if group else 0 for group in match.groups())
        return int(hours * 3600 + minutes * 60 + seconds)

    try:
        hours, minutes, seconds = (float(part) for part in value.split(':'))
        return int(hours * 3600 + minutes * 60 + seconds)
    except (ValueError, IndexError):
        return 0
