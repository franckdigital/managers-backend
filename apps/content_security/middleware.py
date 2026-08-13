LOGGED_PREFIXES = ('/media/', '/api/content-security/')


class AccessLogMiddleware:
    """§25.4 — records every access to protected media/streaming endpoints."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(LOGGED_PREFIXES):
            self._log(request, response)
        return response

    def _log(self, request, response):
        from apps.content_security.models import AccessLog

        tenant_user = getattr(request, 'tenant_user', None)
        user = tenant_user if tenant_user and tenant_user.is_authenticated else None
        try:
            AccessLog.objects.create(
                user=user,
                path=request.path[:500],
                method=request.method,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                status_code=response.status_code,
            )
        except Exception:
            pass
