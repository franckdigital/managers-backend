from django.utils import timezone

from apps.learning_paths.models import LearningPathEnrollment, LearningPathStep


def recompute_path_enrollments_for_course(user, course):
    """§7/§24 — when a course completes, check whether it unblocks completion of any
    learning path the user is following, and if so close out that path's enrollment."""

    steps = LearningPathStep.objects.filter(course=course, is_mandatory=True).select_related('path')
    for step in steps:
        enrollment, _ = LearningPathEnrollment.objects.get_or_create(user=user, path=step.path)
        if enrollment.status == LearningPathEnrollment.STATUS_COMPLETED:
            continue

        mandatory_course_ids = list(
            LearningPathStep.objects.filter(path=step.path, is_mandatory=True).values_list('course_id', flat=True)
        )
        from apps.courses.models import Enrollment

        completed_count = Enrollment.objects.filter(
            user=user, course_id__in=mandatory_course_ids, status=Enrollment.STATUS_COMPLETED
        ).count()
        total = len(mandatory_course_ids)
        progress_percent = round(completed_count / total * 100, 2) if total else 0

        enrollment.progress_percent = progress_percent
        if enrollment.status == LearningPathEnrollment.STATUS_NOT_STARTED:
            enrollment.status = LearningPathEnrollment.STATUS_IN_PROGRESS
            enrollment.started_at = enrollment.started_at or timezone.now()

        if progress_percent >= 100:
            complete_path_enrollment(enrollment)
        else:
            enrollment.save(update_fields=['progress_percent', 'status', 'started_at'])


def complete_path_enrollment(enrollment):
    enrollment.status = LearningPathEnrollment.STATUS_COMPLETED
    enrollment.completed_at = timezone.now()
    enrollment.save(update_fields=['status', 'completed_at', 'progress_percent'])

    if enrollment.path.certificate_enabled:
        from apps.certificates.services import generate_certificate

        generate_certificate(enrollment.user, path=enrollment.path)
    else:
        from apps.notifications.models import Notification
        from apps.notifications.services import notify

        notify(
            enrollment.user,
            'Parcours terminé',
            f"Félicitations, vous avez terminé le parcours « {enrollment.path.title} ».",
            channels=[Notification.CHANNEL_IN_APP, Notification.CHANNEL_EMAIL],
            data={'path_id': enrollment.path_id},
        )
