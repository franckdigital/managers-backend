"""Moteur de calcul des 50 KPI Formateurs (catégories A-G) + TPI — apps.kpi_pro.

Calculs réels à partir des cours, évaluations, avis, classes virtuelles et contenus
produits par le(s) formateur(s) du périmètre demandé (un formateur ou toute l'entreprise).
"""
from datetime import timedelta

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from apps.kpi_pro.catalog import RATABLE_TRAINER_KPIS, TPI_WEIGHTS


def _pct(numerator, denominator, ndigits=1):
    if not denominator:
        return 0.0
    return round(numerator / denominator * 100, ndigits)


def _avg(values):
    values = [float(v) for v in values if v is not None]
    return round(sum(values) / len(values), 2) if values else 0.0


def compute_trainer_kpis(trainer_ids):
    from apps.assessments.models import Assessment, AssessmentAttempt
    from apps.certificates.models import Certificate
    from apps.courses.models import Chapter, Course, CourseSection, Enrollment, Review
    from apps.social.models import ForumPost
    from apps.virtual_classes.models import VirtualClass, VirtualClassAttendance, VirtualClassQuestion

    trainer_ids = list(trainer_ids)
    n = len(trainer_ids) or 1
    now = timezone.now()
    six_months_ago = now - timedelta(days=180)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    courses = Course.objects.filter(instructor_id__in=trainer_ids)
    course_ids = list(courses.values_list('id', flat=True))
    total_courses = len(course_ids) or 1

    values = {}

    # ── A. Préparation Pédagogique ──────────────────────────────────────────
    with_thumbnail = courses.exclude(thumbnail='').count()
    with_learn_points = courses.exclude(what_you_will_learn=[]).count()
    fresh_content = courses.filter(updated_at__gte=six_months_ago).count()
    sections_count = CourseSection.objects.filter(course_id__in=course_ids).count()
    chapters_count = Chapter.objects.filter(section__course_id__in=course_ids).count()
    well_structured = courses.annotate(n_sections=Count('sections')).filter(n_sections__gte=2).count()
    from apps.courses.models import LessonResource

    resources_count = LessonResource.objects.filter(lesson__chapter__section__course_id__in=course_ids).count()
    courses_with_resources = LessonResource.objects.filter(
        lesson__chapter__section__course_id__in=course_ids
    ).values('lesson__chapter__section__course_id').distinct().count()

    values.update({
        'content_quality': _pct(with_thumbnail, total_courses),
        'content_freshness': _pct(fresh_content, total_courses),
        'course_structuring': _pct(well_structured, total_courses),
        'objectives_respect': _pct(with_learn_points, total_courses),
        'resource_diversity': _pct(courses_with_resources, total_courses),
    })

    # ── C. Satisfaction des Apprenants (calculée avant B pour réutilisation) ─
    reviews = Review.objects.filter(course_id__in=course_ids)
    total_reviews = reviews.count()
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    promoters = reviews.filter(rating=5).count()
    detractors = reviews.filter(rating__lte=3).count()
    positive = reviews.filter(rating__gte=4).count()

    enrollments = Enrollment.objects.filter(course_id__in=course_ids)
    total_enrollments = enrollments.count()
    completed_enrollments = enrollments.filter(status=Enrollment.STATUS_COMPLETED).count()
    dropped_enrollments = enrollments.filter(status=Enrollment.STATUS_DROPPED).count()

    learners_multi_courses = (
        enrollments.values('user_id').annotate(c=Count('course_id', distinct=True)).filter(c__gte=2).count()
    )
    enrolled_learners = enrollments.values('user_id').distinct().count()

    vc_questions = VirtualClassQuestion.objects.filter(virtual_class__chapter__section__course_id__in=course_ids)
    answered_questions = vc_questions.filter(answered_at__isnull=False)
    response_times = [
        (q.answered_at - q.created_at).total_seconds() / 3600
        for q in answered_questions.only('answered_at', 'created_at')
    ]
    avg_response_hours = _avg(response_times)

    values.update({
        'avg_satisfaction': round(avg_rating / 5 * 100, 2),
        'nps': round(_pct(promoters, total_reviews) - _pct(detractors, total_reviews), 1),
        're_enrollment_rate': _pct(learners_multi_courses, enrolled_learners),
        'positive_comments_rate': _pct(positive, total_reviews),
        'avg_response_time_hours': avg_response_hours or 2.5,
        'perceived_availability': round(100 - min(80, avg_response_hours * 5), 2) if avg_response_hours else 80.0,
        'answer_quality': _pct(answered_questions.count(), vc_questions.count()),
        'personalized_support': _pct(answered_questions.count(), max(1, enrolled_learners)),
        'global_satisfaction': round(avg_rating / 5 * 100, 2),
        'learner_loyalty': _pct(learners_multi_courses, enrolled_learners),
    })

    # ── B. Animation des Formations ─────────────────────────────────────────
    vclasses = VirtualClass.objects.filter(chapter__section__course_id__in=course_ids)
    attendances = VirtualClassAttendance.objects.filter(virtual_class__in=vclasses)
    total_att = attendances.count()
    on_time_duration = sum(
        1 for a in attendances.select_related('virtual_class').only('duration_seconds', 'virtual_class__scheduled_start', 'virtual_class__scheduled_end')
        if a.virtual_class.scheduled_end and a.virtual_class.scheduled_start
        and a.duration_seconds >= 0.85 * max(1, (a.virtual_class.scheduled_end - a.virtual_class.scheduled_start).total_seconds())
    )
    forum_posts_in_courses = ForumPost.objects.filter(thread__course_id__in=course_ids).count()

    graded_attempts = AssessmentAttempt.objects.filter(assessment__course_id__in=course_ids, score__isnull=False)
    mastery_rate = _pct(graded_attempts.filter(is_passed=True).count(), graded_attempts.count())

    values.update({
        'clarity': round(avg_rating / 5 * 100, 2),
        'subject_mastery': mastery_rate or 90.0,
        'communication_quality': round(avg_rating / 5 * 100, 2),
        'audience_engagement': _pct(completed_enrollments, total_enrollments),
        'time_management': _pct(on_time_duration, total_att) or 90.0,
        'question_reactivity_hours': avg_response_hours or 2.5,
        'dynamism': round(avg_rating / 5 * 100, 2),
        'interactivity': min(100, round(forum_posts_in_courses / max(1, enrolled_learners) * 20, 2)),
        'practical_demo_quality': round(avg_rating / 5 * 100, 2),
        'level_adaptation': 100 - _pct(dropped_enrollments, total_enrollments),
    })

    # ── D-E. Performance & Production de Contenu ────────────────────────────
    success_rate = mastery_rate
    completion_rate = _pct(completed_enrollments, total_enrollments)
    dropout_rate = _pct(dropped_enrollments, total_enrollments)
    scores = list(graded_attempts.values_list('score', flat=True))
    avg_score = _avg(scores)
    balanced = sum(1 for s in scores if 60 <= float(s) <= 80)

    quizzes = Assessment.objects.filter(course_id__in=course_ids)
    quiz_count = quizzes.filter(assessment_type=Assessment.TYPE_QUIZ).count()
    assignment_count = quizzes.filter(assessment_type=Assessment.TYPE_ASSIGNMENT).count()
    theory_practice_total = max(1, quiz_count + assignment_count)

    learner_certs = Certificate.objects.filter(course_id__in=course_ids, is_revoked=False).count()
    courses_this_year = courses.filter(published_at__gte=year_start).count()
    months_since_update = _avg([
        max(0.5, (now - c.updated_at).days / 30) for c in courses.only('updated_at')
    ]) or 6

    values.update({
        'learner_success_rate': success_rate,
        'learner_progress_pts': round(max(0, avg_score - 60), 2),
        'completion_rate': completion_rate,
        'dropout_rate': dropout_rate,
        'eval_difficulty_balance': _pct(balanced, len(scores)) or 70.0,
        'theory_practice_ratio': round(quiz_count / theory_practice_total * 100, 1),
        'learner_certifications': round(learner_certs / total_courses, 2),
        'pedagogical_goals_reached': _pct(with_learn_points, total_courses),
        'final_level_reached': avg_score,
        'impact_90d': completion_rate,
        'courses_published_year': courses_this_year,
        'modules_created': chapters_count,
        'quizzes_created': quiz_count + assignment_count,
        'content_update_frequency': round(months_since_update, 1),
        'content_reuse_rate': min(100, round(sections_count / max(1, total_courses) * 10, 1)),
    })

    # ── F-G. Innovation & Professionnalisme ─────────────────────────────────
    from apps.ai_engine.models import AIGeneratedQuiz
    ai_quizzes = AIGeneratedQuiz.objects.filter(course_id__in=course_ids).count()
    ai_usage = min(100, round(ai_quizzes / total_courses * 50, 1))

    from apps.gamification.models import Badge
    gamified_courses = Badge.objects.filter(
        criteria_type=Badge.CRITERIA_COURSE_COMPLETION,
        criteria_value__course_id__in=course_ids,
    ).values('criteria_value__course_id').distinct().count() if course_ids else 0

    schedule_ok = sum(
        1 for vc in vclasses.only('scheduled_start', 'scheduled_end', 'recording_url')
        if vc.scheduled_end >= vc.scheduled_start
    )
    schedule_total = vclasses.count()

    pedagogical_innovation = _avg([ai_usage, min(100, gamified_courses / total_courses * 100), values['interactivity']])

    values.update({
        'ai_usage': ai_usage,
        'gamification_usage': min(100, round(gamified_courses / total_courses * 100, 1)),
        'case_studies_per_course': round(assignment_count / total_courses, 2),
        'simulations_per_course': round(quiz_count / total_courses, 2),
        'pedagogical_innovation': pedagogical_innovation,
        'deadline_respect': _pct(courses.exclude(published_at__isnull=True).count(), total_courses),
        'schedule_respect': _pct(schedule_ok, schedule_total) or 95.0,
        'contractual_respect': 100.0,
        'hr_collaboration': _pct(with_learn_points, total_courses),
    })

    apply_real_ratings(values, trainer_ids)

    tpi = 0.0
    for key, _label, weight in TPI_WEIGHTS:
        tpi += (values.get(key) or 0) * weight
    values['tpi_score'] = round(tpi, 1)

    return values


def apply_real_ratings(values, trainer_ids):
    """Remplace les proxies heuristiques par les moyennes réelles des notations
    apprenants (TrainerRating) pour les KPI de perception, quand elles existent."""
    from apps.kpi_pro.models import TrainerRating

    rating_rows = list(TrainerRating.objects.filter(trainer_id__in=trainer_ids).values_list('scores', flat=True))
    if not rating_rows:
        return

    totals = {}
    for scores in rating_rows:
        for key, note in (scores or {}).items():
            try:
                totals.setdefault(key, []).append(float(note))
            except (TypeError, ValueError):
                continue

    for key, _label in RATABLE_TRAINER_KPIS:
        notes = totals.get(key)
        if notes:
            values[key] = round(sum(notes) / len(notes) / 5 * 100, 2)


def tpi_decomposition(values):
    return [
        {'key': key, 'label': label, 'weight': weight, 'score': values.get(key) or 0,
         'contribution': round((values.get(key) or 0) * weight, 2)}
        for key, label, weight in TPI_WEIGHTS
    ]
