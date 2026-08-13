from django.conf import settings
from django.core import signing
from django.utils import timezone

from apps.core.constants import Roles

STREAM_TOKEN_SALT = 'lmspro.content_security.stream'


def _user_has_active_enrollment(user, course):
    """§25 — a signed download ticket can outlive a learner's access; re-check the real
    enrollment at the moment of download, not just when the ticket was first issued."""

    if user.is_superuser or getattr(user, 'role', None) in (Roles.SUPER_ADMIN, Roles.COMPANY_ADMIN, Roles.HR):
        return True
    if getattr(course, 'instructor_id', None) == user.id:
        return True

    from apps.courses.models import Enrollment

    return Enrollment.objects.filter(user=user, course=course).exclude(status=Enrollment.STATUS_DROPPED).exists()


def generate_stream_token(user, lesson):
    return signing.dumps({'user_id': user.id, 'lesson_id': lesson.id}, salt=STREAM_TOKEN_SALT)


def verify_stream_token(token):
    ttl = settings.LMSPRO_CONTENT_SECURITY['SIGNED_URL_TTL_SECONDS']
    try:
        return signing.loads(token, salt=STREAM_TOKEN_SALT, max_age=ttl)
    except signing.BadSignature:
        return None


def _within_download_window(start, end):
    now = timezone.now()
    if start and now < start:
        return False
    if end and now > end:
        return False
    return True


def _user_matches_profiles(user, profiles):
    if not profiles:
        return True
    for profile in profiles:
        if profile == 'premium' and user.is_premium:
            return True
        if profile == 'company' and user.is_b2b:
            return True
        if profile == user.role:
            return True
    return False


def can_download_lesson(lesson, user):
    from apps.progression.services import get_progression_settings

    if not lesson.download_allowed:
        return False

    if not _user_has_active_enrollment(user, lesson.course):
        return False

    course_settings = get_progression_settings(lesson.course)
    base_allowed = (
        course_settings.download_videos_allowed
        if lesson.content_type == lesson.TYPE_VIDEO
        else course_settings.download_documents_allowed
    )
    if not base_allowed:
        return False

    if not _within_download_window(lesson.download_window_start, lesson.download_window_end):
        return False

    return _user_matches_profiles(user, lesson.download_profiles)


def can_download_resource(resource, user):
    if not resource.download_allowed:
        return False
    if not _user_has_active_enrollment(user, resource.lesson.course):
        return False
    if not _within_download_window(resource.download_window_start, resource.download_window_end):
        return False
    return _user_matches_profiles(user, resource.download_profiles)


def is_origin_allowed(request):
    """§25 — media URLs are signed and short-lived, but without this check they'd still
    work if pasted straight into a new tab or fetched with curl, bypassing the player's
    right-click/download blocking entirely. Requiring a matching Origin/Referer closes
    that casual bypass (headers are spoofable, so this is dissuasion, not a hard
    guarantee — the token TTL and per-user AccessLog trail are the real backstop)."""
    origin = request.META.get('HTTP_ORIGIN') or request.META.get('HTTP_REFERER')
    if not origin:
        return False
    return any(origin.startswith(allowed) for allowed in settings.CORS_ALLOWED_ORIGINS)
