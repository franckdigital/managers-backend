import random
from datetime import timedelta

from django.utils import timezone

from apps.assessments.models import Assessment, AssessmentAttempt, AssessmentQuestion, Question


def start_attempt(assessment, user):
    from apps.progression.services import get_progression_settings

    if assessment.chapter_id is None:
        # Course-level final exam: only accessible once the learner has finished 100% of the lessons.
        from apps.courses.models import Enrollment

        progress = (
            Enrollment.objects.filter(user=user, course=assessment.course)
            .values_list('progress_percent', flat=True)
            .first()
        )
        if progress is None or progress < 100:
            raise ValueError("Vous devez terminer 100% de la formation avant de passer cette évaluation.")

    previous = AssessmentAttempt.objects.filter(assessment=assessment, user=user).count()
    course_settings = get_progression_settings(assessment.course)
    effective_max = assessment.max_attempts
    if course_settings.max_attempts is not None:
        effective_max = min(effective_max, course_settings.max_attempts)

    if previous >= effective_max:
        raise ValueError('Nombre maximal de tentatives atteint.')

    questions = build_question_set(assessment)
    attempt = AssessmentAttempt.objects.create(
        assessment=assessment,
        user=user,
        attempt_number=previous + 1,
        questions_snapshot=[q.id for q in questions],
    )

    from apps.progression.services import record_xapi_statement

    record_xapi_statement(user, 'attempted', 'assessment', assessment.id, object_name=assessment.title)
    return attempt


def is_attempt_expired(attempt):
    """§7 — examen chronométré: once the time limit has elapsed, the attempt can no
    longer be answered and must be auto-submitted with whatever was answered so far."""

    if not attempt.assessment.time_limit_minutes:
        return False
    if attempt.status != AssessmentAttempt.STATUS_IN_PROGRESS:
        return False
    deadline = attempt.started_at + timedelta(minutes=attempt.assessment.time_limit_minutes)
    return timezone.now() > deadline


def record_proctoring_event(attempt, event_type, details=None):
    """§7 — examen anti-fraude: accumulates suspicious signals reported during the attempt
    (tab switch, fullscreen exit, multiple faces detected, etc.) for later review."""

    event = {
        'event_type': event_type,
        'details': details or {},
        'recorded_at': timezone.now().isoformat(),
    }
    attempt.proctoring_flags = [*attempt.proctoring_flags, event]
    attempt.save(update_fields=['proctoring_flags'])
    return attempt


def build_question_set(assessment):
    if assessment.is_randomized and assessment.question_bank_id:
        pool = list(assessment.question_bank.questions.all())
        random.shuffle(pool)
        size = assessment.question_pool_size or len(pool)
        return pool[:size]
    return list(
        Question.objects.filter(
            id__in=AssessmentQuestion.objects.filter(assessment=assessment).order_by('order').values_list('question_id', flat=True)
        )
    )


def grade_answer(question, answer):
    if question.question_type in (Question.TYPE_MCQ, Question.TYPE_TRUE_FALSE):
        correct_ids = set(question.choices.filter(is_correct=True).values_list('id', flat=True))
        selected_ids = set(answer.selected_choices.values_list('id', flat=True))
        is_correct = selected_ids == correct_ids and len(selected_ids) > 0
        return is_correct, question.points if is_correct else 0

    if question.question_type == Question.TYPE_OPEN_TEXT:
        accepted = [a.strip().lower() for a in question.metadata.get('accepted_answers', [])]
        if accepted:
            is_correct = answer.text_answer.strip().lower() in accepted
            return is_correct, question.points if is_correct else 0

        from apps.ai_engine.services import grade_open_text_with_ai

        is_correct, _confidence = grade_open_text_with_ai(question, answer.text_answer)
        if is_correct is None:
            return None, 0
        return is_correct, question.points if is_correct else 0

    if question.question_type in (Question.TYPE_MATCHING, Question.TYPE_DRAG_DROP):
        expected = question.metadata.get('pairs') or question.metadata.get('mapping') or {}
        is_correct = answer.matching_answer == expected
        return is_correct, question.points if is_correct else 0

    return None, 0


def grade_attempt(attempt, timed_out=False):
    # total_points must reflect every question in the attempt's snapshot, not just the ones
    # the learner actually answered — otherwise skipping questions doesn't cost any points.
    snapshot_questions = Question.objects.filter(id__in=attempt.questions_snapshot)
    total_points = sum(q.points for q in snapshot_questions)
    earned_points = 0
    needs_manual_grading = False

    answered_by_question = {
        answer.question_id: answer
        for answer in attempt.answers.select_related('question').prefetch_related('selected_choices')
    }
    for question in snapshot_questions:
        answer = answered_by_question.get(question.id)
        if answer is None:
            continue  # left blank — contributes 0 earned points but still counts in total_points
        is_correct, points = grade_answer(question, answer)
        answer.is_correct = is_correct
        answer.points_awarded = points
        answer.save(update_fields=['is_correct', 'points_awarded'])
        earned_points += points
        if is_correct is None:
            needs_manual_grading = True

    score = (earned_points / total_points * 100) if total_points else 0
    attempt.score = round(score, 2)
    attempt.is_passed = score >= attempt.assessment.passing_score
    attempt.submitted_at = timezone.now()
    if timed_out:
        attempt.status = AssessmentAttempt.STATUS_EXPIRED
    else:
        attempt.status = AssessmentAttempt.STATUS_SUBMITTED if needs_manual_grading else AssessmentAttempt.STATUS_GRADED
    attempt.save(update_fields=['score', 'is_passed', 'submitted_at', 'status'])

    if attempt.is_passed:
        from apps.gamification.services import award_quiz_pass_xp

        award_quiz_pass_xp(attempt.user, attempt.assessment)

    if not needs_manual_grading:
        from apps.progression.services import record_xapi_statement

        record_xapi_statement(
            attempt.user, 'passed' if attempt.is_passed else 'failed', 'assessment', attempt.assessment_id,
            object_name=attempt.assessment.title, result={'success': attempt.is_passed, 'score': {'scaled': round(score / 100, 2)}},
        )

    if attempt.assessment.chapter_id is None and attempt.score is not None and attempt.score >= 100:
        # Passing the course's final exam with a perfect score is what unlocks the certificate
        # for courses that have one — see apps.certificates.services.maybe_issue_certificate_for_course.
        # Best-effort: PDF/QR generation is a side effect and must never fail the exam submission.
        try:
            from apps.certificates.services import maybe_issue_certificate_for_course

            maybe_issue_certificate_for_course(attempt.user, attempt.assessment.course)
        except Exception:
            import logging

            logging.getLogger(__name__).exception(
                'Certificate issuance failed after a perfect final-exam score (attempt=%s)', attempt.id
            )

    return attempt
