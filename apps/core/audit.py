from apps.core.models import AuditLog


def _client_ip(request):
    if request is None:
        return None
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_audit(user, action, instance, changes=None, request=None):
    AuditLog.objects.create(
        user=user if getattr(user, 'is_authenticated', False) else None,
        company=getattr(user, 'company', None),
        action=action,
        model_name=instance.__class__.__name__,
        object_id=str(instance.pk),
        object_repr=str(instance)[:255],
        changes=changes or {},
        ip_address=_client_ip(request),
    )
