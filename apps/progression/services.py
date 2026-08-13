from django.db.models import F
from django.utils import timezone

from apps.progression.models import ChapterUnlock, ChapterValidation, CourseProgressionSettings, CourseView, LessonProgress, XAPIStatement

XAPI_VERB_IRIS = {
    'experienced': 'http://adlnet.gov/expapi/verbs/experienced',
    'attempted': 'http://adlnet.gov/expapi/verbs/attempted',
    'completed': 'http://adlnet.gov/expapi/verbs/completed',
    'passed': 'http://adlnet.gov/expapi/verbs/passed',
    'failed': 'http://adlnet.gov/expapi/verbs/failed',
}


def record_xapi_statement(user, verb, object_type, object_id, object_name='', result=None):
    """Minimal LRS write (actor/verb/object/result), using real ADL xAPI verb IRIs —
    cahier §23. Called from every key learning event, not left as a dangling model."""

    statement = {
        'actor': {'mbox': f'mailto:{user.email}', 'name': user.get_full_name() or user.email},
        'verb': {'id': XAPI_VERB_IRIS.get(verb, verb), 'display': {'en-US': verb}},
        'object': {
            'id': f'urn:lmspro:{object_type}:{object_id}',
            'definition': {'name': {'en-US': object_name}} if object_name else {},
        },
        'result': result or {},
        'timestamp': timezone.now().isoformat(),
    }
    return XAPIStatement.objects.create(
        user=user, verb=verb, object_type=object_type, object_id=str(object_id),
        result=result or {}, raw_statement=statement,
    )


_XAPI_VERB_FOR_EVENT = {
    'open':              'experienced',
    'play':              'experienced',
    'pause':             'experienced',
    'resume':            'experienced',
    'complete':          'completed',
    'document_view':     'experienced',
    'document_download': 'experienced',
}


def record_lesson_event(user, lesson, verb, position_seconds=None, time_spent_delta=0):
    """Enregistre un événement discret d'apprentissage (open, play, pause…) et met à jour
    les compteurs sur LessonProgress de façon atomique (F-expressions), puis écrit un
    statement xAPI."""

    LessonProgress.objects.get_or_create(user=user, lesson=lesson)

    updates = {}
    if verb == 'open':
        updates['open_count'] = F('open_count') + 1
        updates['last_opened_at'] = timezone.now()
    elif verb in ('play', 'resume'):
        updates['video_play_count'] = F('video_play_count') + 1
    elif verb == 'document_view':
        updates['document_viewed'] = True

    if time_spent_delta:
        updates['time_spent_seconds'] = F('time_spent_seconds') + time_spent_delta

    if updates:
        LessonProgress.objects.filter(user=user, lesson=lesson).update(**updates)

    record_xapi_statement(
        user=user,
        verb=_XAPI_VERB_FOR_EVENT.get(verb, 'experienced'),
        object_type='lesson',
        object_id=lesson.id,
        object_name=lesson.title,
        result={'verb_detail': verb, 'position_seconds': position_seconds},
    )

    # Si document ouvert → recalculer la progression du cours
    if verb == 'document_view':
        recompute_enrollment_progress(user, lesson.course)


def record_course_view(user, course):
    """Incrémente atomiquement le compteur d'ouvertures de la page cours pour cet utilisateur."""
    obj, created = CourseView.objects.get_or_create(user=user, course=course)
    if not created:
        CourseView.objects.filter(pk=obj.pk).update(open_count=F('open_count') + 1)


def get_progression_settings(course):
    settings_obj, _ = CourseProgressionSettings.objects.get_or_create(course=course)
    return settings_obj


def ordered_chapters(course):
    from apps.courses.models import Chapter

    return list(Chapter.objects.filter(section__course=course).select_related('section').order_by('section__order', 'order'))


def is_lesson_completed(progress, lesson, settings):
    from apps.courses.models import Lesson

    if progress is None:
        return False
    if lesson.content_type == Lesson.TYPE_VIDEO:
        if progress.watch_percent < settings.min_video_watch_percent:
            return False
        if settings.min_watch_time_seconds and progress.time_spent_seconds < settings.min_watch_time_seconds:
            return False
        return True
    if lesson.content_type in (Lesson.TYPE_PDF, Lesson.TYPE_WORD, Lesson.TYPE_PPT, Lesson.TYPE_ZIP, Lesson.TYPE_IMAGE):
        return progress.document_viewed
    return progress.is_completed


def is_chapter_completed(user, chapter, settings=None):
    settings = settings or get_progression_settings(chapter.course)

    progresses = {
        p.lesson_id: p for p in LessonProgress.objects.filter(user=user, lesson__chapter=chapter)
    }
    for lesson in chapter.lessons.all():
        progress = progresses.get(lesson.id)
        if not progress or not progress.is_completed:
            return False

    if settings.quiz_required:
        from apps.assessments.models import Assessment, AssessmentAttempt

        for assessment in Assessment.objects.filter(chapter=chapter, is_published=True):
            passed = AssessmentAttempt.objects.filter(assessment=assessment, user=user, is_passed=True).exists()
            if not passed:
                return False

    if settings.trainer_validation_required or settings.manager_hr_validation_required:
        if not ChapterValidation.objects.filter(user=user, chapter=chapter).exists():
            return False

    if settings.virtual_class_attendance_required:
        from apps.virtual_classes.models import VirtualClass, VirtualClassAttendance

        for virtual_class in VirtualClass.objects.filter(chapter=chapter):
            attended = VirtualClassAttendance.objects.filter(
                virtual_class=virtual_class, user=user, joined_at__isnull=False
            ).exists()
            if not attended:
                return False

    if settings.attendance_signature_required:
        from apps.virtual_classes.models import AttendanceSignature, VirtualClass

        for virtual_class in VirtualClass.objects.filter(chapter=chapter):
            signed = AttendanceSignature.objects.filter(virtual_class=virtual_class, user=user).exists()
            if not signed:
                return False

    return True


def is_chapter_unlocked(user, chapter):
    settings = get_progression_settings(chapter.course)
    if not settings.sequential_enabled:
        return True

    chapters = ordered_chapters(chapter.course)
    index = next((i for i, c in enumerate(chapters) if c.id == chapter.id), None)
    if index is None or index == 0:
        return True

    previous_chapter = chapters[index - 1]
    unlocked = is_chapter_completed(user, previous_chapter, settings)
    if unlocked:
        ChapterUnlock.objects.get_or_create(user=user, chapter=chapter)
    return unlocked


def is_final_exam_unlocked(user, course):
    settings = get_progression_settings(course)
    if not settings.sequential_enabled:
        return True
    return all(is_chapter_completed(user, chapter, settings) for chapter in ordered_chapters(course))


def is_previous_lesson_completed(user, lesson):
    """§26 — within an unlocked chapter, lessons must still be taken in order: lesson N+1
    stays locked until lesson N (by `order`, same chapter) is completed."""
    settings = get_progression_settings(lesson.course)
    if not settings.sequential_enabled:
        return True

    siblings = list(lesson.chapter.lessons.order_by('order'))
    index = next((i for i, l in enumerate(siblings) if l.id == lesson.id), None)
    if index is None or index == 0:
        return True

    previous_lesson = siblings[index - 1]
    progress = LessonProgress.objects.filter(user=user, lesson=previous_lesson).first()
    return bool(progress and progress.is_completed)


def is_lesson_accessible(user, lesson):
    if lesson.is_preview_free:
        return True
    if not is_chapter_unlocked(user, lesson.chapter):
        return False
    return is_previous_lesson_completed(user, lesson)


MAX_PLAYBACK_RATE_TOLERANCE = 4  # generous allowance for e.g. 2x playback + buffering jitter
MIN_ELAPSED_SLACK_SECONDS = 15   # floor so back-to-back calls (e.g. timeupdate then ended) aren't over-penalized


def record_lesson_progress(
    user, lesson, watched_seconds=None, position_seconds=None, document_viewed=None, time_spent_delta=0,
    scorm_completed=None, duration_seconds=None,
):
    from apps.courses.models import Lesson

    progress, created = LessonProgress.objects.get_or_create(user=user, lesson=lesson)
    settings = get_progression_settings(lesson.course)

    if created:
        record_xapi_statement(user, 'experienced', 'lesson', lesson.id, object_name=lesson.title)

    # Backfill a lesson's duration from what the player actually reports — authors
    # frequently leave "Durée (secondes)" at 0, which otherwise blocks watch_percent
    # from ever being computed below and silently prevents the lesson from completing.
    if duration_seconds and not lesson.duration_seconds:
        lesson.duration_seconds = duration_seconds
        lesson.save(update_fields=['duration_seconds'])

    if watched_seconds is not None:
        # §26 anti-skip: a client can't inflate "furthest position reached" faster than
        # realistic playback could have covered since the last update — this is what
        # stops scrubbing straight to the end (or a crafted API call) from instantly
        # completing a video. Rewinding/replaying is unaffected (max() only grows).
        if not created and lesson.content_type == Lesson.TYPE_VIDEO:
            elapsed = (timezone.now() - progress.updated_at).total_seconds()
            max_allowed = progress.watched_seconds + max(elapsed, MIN_ELAPSED_SLACK_SECONDS) * MAX_PLAYBACK_RATE_TOLERANCE
            watched_seconds = min(watched_seconds, max_allowed)
        progress.watched_seconds = max(progress.watched_seconds, watched_seconds)
        if lesson.duration_seconds:
            progress.watch_percent = min(100, round(progress.watched_seconds / lesson.duration_seconds * 100, 2))
    if position_seconds is not None:
        progress.last_position_seconds = position_seconds
    if document_viewed is not None:
        progress.document_viewed = document_viewed
    if time_spent_delta:
        progress.time_spent_seconds += time_spent_delta

    was_completed = progress.is_completed
    if scorm_completed is not None:
        progress.is_completed = scorm_completed
    else:
        progress.is_completed = is_lesson_completed(progress, lesson, settings)
    if progress.is_completed and not was_completed:
        progress.completed_at = timezone.now()

    progress.save()

    if progress.is_completed and not was_completed:
        from apps.gamification.services import award_lesson_completion_xp

        award_lesson_completion_xp(user, lesson)
        record_xapi_statement(user, 'completed', 'lesson', lesson.id, object_name=lesson.title)

    recompute_enrollment_progress(user, lesson.course)
    return progress


def recompute_enrollment_progress(user, course):
    from apps.courses.models import Enrollment, Lesson

    enrollment, _ = Enrollment.objects.get_or_create(
        user=user, course=course, defaults={'source': Enrollment.SOURCE_FREE}
    )

    total_lessons = Lesson.objects.filter(chapter__section__course=course).count()
    completed_lessons = LessonProgress.objects.filter(
        user=user, lesson__chapter__section__course=course, is_completed=True
    ).count()

    progress_percent = round(completed_lessons / total_lessons * 100, 2) if total_lessons else 0
    enrollment.progress_percent = progress_percent

    if progress_percent >= 100 and enrollment.status != Enrollment.STATUS_COMPLETED:
        complete_enrollment(enrollment)
    else:
        enrollment.save(update_fields=['progress_percent'])

    return enrollment


def complete_enrollment(enrollment):
    from apps.courses.models import Enrollment

    enrollment.status = Enrollment.STATUS_COMPLETED
    enrollment.completed_at = timezone.now()
    enrollment.save(update_fields=['status', 'completed_at', 'progress_percent'])

    user, course = enrollment.user, enrollment.course
    record_xapi_statement(
        user, 'completed', 'course', course.id, object_name=course.title,
        result={'completion': True},
    )

    from apps.gamification.services import award_course_completion_badges, award_skill_gain_xp, award_xp
    from apps.hr_analytics.services import update_employee_skills_from_course

    award_xp(user, 100, f'Formation terminée: {course.title}', source_type='course', source_id=course.id)
    award_course_completion_badges(user, course)
    for employee_skill, levels_gained in update_employee_skills_from_course(user, course):
        award_skill_gain_xp(user, employee_skill, levels_gained)

    # Best-effort: PDF/QR generation is a side effect and must never fail lesson-progress
    # tracking (the request that triggers this on 100% completion).
    try:
        from apps.certificates.services import maybe_issue_certificate_for_course

        maybe_issue_certificate_for_course(user, course)
    except Exception:
        import logging

        logging.getLogger(__name__).exception(
            'Certificate issuance failed on course completion (enrollment=%s)', enrollment.id
        )

    from apps.learning_paths.services import recompute_path_enrollments_for_course

    recompute_path_enrollments_for_course(user, course)
