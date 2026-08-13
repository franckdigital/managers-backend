import uuid

from django.conf import settings
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import UserDevice


def blacklist_jti(jti):
    try:
        token = OutstandingToken.objects.get(jti=jti)
    except OutstandingToken.DoesNotExist:
        return
    BlacklistedToken.objects.get_or_create(token=token)


def register_device(user, device_id, request, refresh_token_str):
    """Registers the device used for this login and enforces the concurrent-device limit
    (cahier des charges §25.4) by blacklisting the refresh tokens of the oldest excess devices."""

    device_id = device_id or str(uuid.uuid4())
    jti = RefreshToken(refresh_token_str)['jti']
    ip = request.META.get('REMOTE_ADDR') if request else None
    ua = (request.META.get('HTTP_USER_AGENT', '') if request else '')[:500]

    UserDevice.objects.update_or_create(
        user=user,
        device_id=device_id,
        defaults={'ip_address': ip, 'user_agent': ua, 'refresh_token_jti': jti, 'is_active': True},
    )

    max_devices = settings.LMSPRO_CONTENT_SECURITY['MAX_CONCURRENT_DEVICES']
    active_devices = list(UserDevice.objects.filter(user=user, is_active=True).order_by('-last_seen'))
    for stale in active_devices[max_devices:]:
        stale.is_active = False
        stale.save(update_fields=['is_active'])
        if stale.refresh_token_jti:
            blacklist_jti(stale.refresh_token_jti)

    return device_id
