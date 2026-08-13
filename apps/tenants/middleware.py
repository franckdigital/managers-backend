from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

_jwt_auth = JWTAuthentication()


class CurrentTenantMiddleware:
    """Resolves the authenticated user/company as early as possible in the request
    lifecycle (works for both JWT API calls and session-based admin access), so that
    downstream middleware (e.g. content access logging) and viewsets can rely on
    request.company without re-running authentication."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant_user = None
        request.company = None

        auth_result = None
        try:
            auth_result = _jwt_auth.authenticate(request)
        except (InvalidToken, TokenError):
            auth_result = None

        if auth_result is not None:
            user, _token = auth_result
            request.tenant_user = user
            request.company = getattr(user, 'company', None)
        elif getattr(request, 'user', None) is not None and request.user.is_authenticated:
            request.tenant_user = request.user
            request.company = getattr(request.user, 'company', None)

        return self.get_response(request)
