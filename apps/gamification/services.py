from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from apps.gamification.models import Badge, Level, UserBadge, UserStreak, XPLog


def get_total_xp(user):
    return user.xp_logs.aggregate(total=Sum('amount'))['total'] or 0


def get_current_level(user):
    total_xp = get_total_xp(user)
    return Level.objects.filter(min_xp__lte=total_xp).order_by('-min_xp').first()


def _notify_badge_earned(user, badge):
    from apps.notifications.services import notify_user

    notify_user(
        user, 'Nouveau badge débloqué !', f'Vous avez obtenu le badge « {badge.title} ».',
        data={'badge_id': badge.id},
    )


def _notify_level_up(user, level):
    from apps.notifications.services import notify_user

    notify_user(
        user, 'Niveau supérieur !', f'Félicitations, vous êtes maintenant niveau « {level.name} ».',
        data={'level_id': level.id},
    )


def award_xp(user, amount, reason, source_type='', source_id=None):
    previous_level = get_current_level(user)
    XPLog.objects.create(user=user, amount=amount, reason=reason, source_type=source_type, source_id=source_id)
    check_xp_threshold_badges(user)
    new_level = get_current_level(user)
    if new_level and new_level != previous_level:
        _notify_level_up(user, new_level)


def award_xp_once(user, amount, reason, source_type, source_id):
    """Like award_xp, but a no-op if this exact (user, source_type, source_id) already
    earned XP — guards lesson/quiz-level rewards against retries/double-counting."""

    if XPLog.objects.filter(user=user, source_type=source_type, source_id=source_id).exists():
        return None
    award_xp(user, amount, reason, source_type=source_type, source_id=source_id)
    return True


def award_lesson_completion_xp(user, lesson):
    award_xp_once(user, 5, f'Leçon terminée : {lesson.title}', source_type='lesson', source_id=lesson.id)


def award_quiz_pass_xp(user, assessment):
    award_xp_once(user, 20, f'Évaluation réussie : {assessment.title}', source_type='assessment_pass', source_id=assessment.id)


def award_skill_gain_xp(user, employee_skill, levels_gained):
    award_xp(
        user, levels_gained * 10, f'Progression de compétence : {employee_skill.skill.name}',
        source_type='skill', source_id=employee_skill.skill_id,
    )
    if employee_skill.level >= 5:
        check_skill_mastery_badges(user, employee_skill.skill)


def check_skill_mastery_badges(user, skill):
    eligible = Badge.objects.filter(criteria_type=Badge.CRITERIA_SKILL_MASTERY)
    for badge in eligible:
        skill_id = badge.criteria_value.get('skill_id')
        if skill_id is None or skill_id == skill.id:
            _, created = UserBadge.objects.get_or_create(user=user, badge=badge)
            if created:
                _notify_badge_earned(user, badge)


def check_xp_threshold_badges(user):
    total_xp = get_total_xp(user)
    eligible = Badge.objects.filter(criteria_type=Badge.CRITERIA_XP_THRESHOLD)
    for badge in eligible:
        threshold = badge.criteria_value.get('xp', None)
        if threshold is not None and total_xp >= threshold:
            _, created = UserBadge.objects.get_or_create(user=user, badge=badge)
            if created:
                _notify_badge_earned(user, badge)


def award_course_completion_badges(user, course):
    eligible = Badge.objects.filter(criteria_type=Badge.CRITERIA_COURSE_COMPLETION)
    for badge in eligible:
        course_id = badge.criteria_value.get('course_id')
        if course_id is None or course_id == course.id:
            _, created = UserBadge.objects.get_or_create(user=user, badge=badge)
            if created:
                _notify_badge_earned(user, badge)


def check_streak_badges(user, current_streak):
    eligible = Badge.objects.filter(criteria_type=Badge.CRITERIA_STREAK)
    for badge in eligible:
        threshold = badge.criteria_value.get('days')
        if threshold is not None and current_streak >= threshold:
            _, created = UserBadge.objects.get_or_create(user=user, badge=badge)
            if created:
                _notify_badge_earned(user, badge)


def record_daily_activity(user):
    """Called on login to track consecutive-day (login streak) activity.
    Resets to 1 if a day was skipped, increments if the previous active day was yesterday,
    is a no-op if already recorded today."""

    today = timezone.localdate()
    streak, _ = UserStreak.objects.get_or_create(user=user)
    if streak.last_active_date == today:
        return streak

    if streak.last_active_date == today - timedelta(days=1):
        streak.current_streak += 1
    else:
        streak.current_streak = 1
    streak.last_active_date = today
    streak.longest_streak = max(streak.longest_streak, streak.current_streak)
    streak.save(update_fields=['current_streak', 'longest_streak', 'last_active_date'])

    check_streak_badges(user, streak.current_streak)
    return streak
