import json

from apps.ai_engine.models import CourseRecommendation, DifficultyAlert


def generate_recommendations_for_user(user, limit=5):
    """Retrieval (DB-bound, cheap) narrows candidates to courses related to what the
    learner has already taken; the AI provider then ranks and justifies the shortlist —
    an LLM can't scan the whole catalog itself, but it can reason over a small candidate set."""

    from apps.courses.models import Course

    enrolled_category_ids = Course.objects.filter(enrollments__user=user).values_list('category_id', flat=True)
    candidates = list(
        Course.objects.filter(status=Course.STATUS_PUBLISHED, category_id__in=list(enrolled_category_ids))
        .exclude(enrollments__user=user)
        .select_related('category')
        .distinct()[: limit * 3]
    )

    if not candidates:
        return []

    ranked = _rank_candidates_with_ai(user, candidates, limit)

    recommendations = []
    for course, score, reason in ranked:
        recommendation, _ = CourseRecommendation.objects.update_or_create(
            user=user, course=course, defaults={'score': score, 'reason': reason},
        )
        recommendations.append(recommendation)
    return recommendations


def _rank_candidates_with_ai(user, candidates, limit):
    from apps.ai_engine.providers import get_ai_provider

    by_id = {course.id: course for course in candidates}
    catalog_text = '\n'.join(
        f'- id={course.id} | {course.title} | catégorie: {course.category.name if course.category else "?"} | '
        f'{(course.subtitle or "")[:120]}'
        for course in candidates
    )
    prompt = (
        f"Voici les formations déjà suivies par l'apprenant {user.get_full_name() or user.email}, et une liste de "
        f"formations candidates. Choisis les {limit} plus pertinentes et réponds UNIQUEMENT avec un tableau JSON "
        '[{"course_id": int, "score": int (0-100), "reason": str (1 phrase, en français)}], sans texte autour.\n\n'
        f'Candidates:\n{catalog_text}'
    )

    try:
        provider = get_ai_provider()
        raw = provider.chat([{'role': 'user', 'content': prompt}])
        parsed = json.loads(raw)
        ranked = []
        for entry in parsed[:limit]:
            course = by_id.get(entry.get('course_id'))
            if course:
                ranked.append((course, int(entry.get('score', 70)), entry.get('reason') or 'Recommandé par l’IA'))
        if ranked:
            return ranked
    except Exception:
        pass

    return [
        (course, 75, 'Basé sur vos formations dans la même catégorie') for course in candidates[:limit]
    ]


def grade_open_text_with_ai(question, text_answer):
    """§Correction automatique — fallback used when a question has no pre-configured
    `accepted_answers`: ask the AI provider to judge the free-text answer against the
    question (and its explanation, if any, as the reference). Returns (is_correct, confidence)
    or (None, 0) if the AI call/parsing fails, so the caller can fall back to manual grading."""

    from apps.ai_engine.providers import get_ai_provider

    if not text_answer or not text_answer.strip():
        return None, 0

    prompt = (
        "Tu es un correcteur pédagogique. Évalue si la réponse de l'apprenant est correcte pour la question "
        "suivante. Réponds UNIQUEMENT avec un objet JSON {\"correct\": bool, \"confidence\": float (0-1)}, "
        "sans texte autour.\n\n"
        f"Question: {question.text}\n"
        f"Référence/explication attendue: {question.explanation or '(aucune fournie, juge sur le bon sens)'}\n"
        f"Réponse de l'apprenant: {text_answer}"
    )

    try:
        provider = get_ai_provider()
        raw = provider.chat([{'role': 'user', 'content': prompt}])
        parsed = json.loads(raw)
        confidence = float(parsed.get('confidence', 0))
        if confidence < 0.6:
            return None, confidence
        return bool(parsed.get('correct')), confidence
    except Exception:
        return None, 0


def detect_learning_difficulties(user):
    from apps.assessments.models import AssessmentAttempt

    alerts = []
    failing_course_ids = (
        AssessmentAttempt.objects.filter(user=user, is_passed=False)
        .values_list('assessment__course_id', flat=True)
        .distinct()
    )
    for course_id in failing_course_ids:
        failed_count = AssessmentAttempt.objects.filter(
            user=user, assessment__course_id=course_id, is_passed=False
        ).count()
        if failed_count >= 2:
            alert, _ = DifficultyAlert.objects.get_or_create(
                user=user, course_id=course_id, signal_type=DifficultyAlert.SIGNAL_REPEATED_FAILURE, is_resolved=False,
                defaults={'details': {'failed_attempts': failed_count}},
            )
            alerts.append(alert)

    from apps.courses.models import Enrollment

    slow_enrollments = Enrollment.objects.filter(user=user, progress_percent__lt=20)
    for enrollment in slow_enrollments:
        alert, _ = DifficultyAlert.objects.get_or_create(
            user=user, course=enrollment.course, signal_type=DifficultyAlert.SIGNAL_SLOW_PROGRESS, is_resolved=False,
            defaults={'details': {'progress_percent': float(enrollment.progress_percent)}},
        )
        alerts.append(alert)

    return alerts
