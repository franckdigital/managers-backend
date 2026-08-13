from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class DeviceAwareJWTAuthentication(JWTAuthentication):
    """Wraps the standard JWT auth with a live device check (§25.4 — déconnexion
    automatique en cas de partage de compte). If the client sends X-Device-Id, that
    device must still be active; revoking a device (or getting evicted by the
    concurrent-device limit) takes effect on the very next request, rather than
    waiting for the short-lived access token to expire on its own."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, validated_token = result
        device_id = request.META.get('HTTP_X_DEVICE_ID')
        if device_id and not user.devices.filter(device_id=device_id, is_active=True).exists():
            raise AuthenticationFailed('Session révoquée sur cet appareil. Veuillez vous reconnecter.')

        return user, validated_token
