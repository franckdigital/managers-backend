from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from apps.integrations.models import APIClient


class APIKeyAuthentication(BaseAuthentication):
    """Authenticates third-party integration requests via X-API-Key / X-API-Secret headers
    (cahier §10 — API publiques). Returns (None, client) — these calls act on behalf of a
    company integration, not a specific human user."""

    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')
        api_secret = request.META.get('HTTP_X_API_SECRET')
        if not api_key or not api_secret:
            return None

        try:
            client = APIClient.objects.get(api_key=api_key, is_active=True)
        except APIClient.DoesNotExist:
            raise AuthenticationFailed("Clé d'API invalide.")

        if not client.check_secret(api_secret):
            raise AuthenticationFailed("Secret d'API invalide.")

        return None, client
