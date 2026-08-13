import hashlib
import hmac

from django.conf import settings
from django.utils import timezone

from apps.virtual_classes.models import AttendanceSignature


def _compute_signature_hash(virtual_class_id, user_id, signed_name, signed_at):
    message = f'{virtual_class_id}:{user_id}:{signed_name}:{signed_at.isoformat()}'.encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


def sign_attendance(virtual_class, user, signed_name, ip_address=None):
    signed_at = timezone.now()
    signature_hash = _compute_signature_hash(virtual_class.id, user.id, signed_name, signed_at)

    signature, _ = AttendanceSignature.objects.update_or_create(
        virtual_class=virtual_class,
        user=user,
        defaults={
            'signed_name': signed_name, 'ip_address': ip_address,
            'signature_hash': signature_hash, 'signed_at': signed_at,
        },
    )
    return signature


def verify_attendance_signature(signature):
    expected = _compute_signature_hash(signature.virtual_class_id, signature.user_id, signature.signed_name, signature.signed_at)
    return hmac.compare_digest(expected, signature.signature_hash)
