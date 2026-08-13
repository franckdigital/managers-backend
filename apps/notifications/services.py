import requests
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.notifications.models import Notification


def send_notification(user, channel, title, message, data=None):
    notification = Notification.objects.create(user=user, channel=channel, title=title, message=message, data=data or {})

    preference = getattr(user, 'notification_preference', None)
    if preference and not getattr(preference, f'{channel}_enabled', True):
        notification.status = Notification.STATUS_FAILED
        notification.data = {**notification.data, 'error': 'Canal désactivé par préférence utilisateur'}
        notification.save(update_fields=['status', 'data'])
        return notification

    try:
        _DISPATCHERS[channel](user, title, message)
        notification.status = Notification.STATUS_SENT
        notification.sent_at = timezone.now()
    except Exception as exc:
        notification.status = Notification.STATUS_FAILED
        notification.data = {**notification.data, 'error': str(exc)}

    notification.save()
    return notification


def notify(user, title, message, channels=None, data=None):
    channels = channels or [Notification.CHANNEL_IN_APP]
    return [send_notification(user, channel, title, message, data) for channel in channels]


def notify_user(user, title, message, data=None):
    """Dispatches on every channel the user has opted into (NotificationPreference),
    instead of a hardcoded channel list — falls back to in-app + email if no preference exists yet."""

    preference = getattr(user, 'notification_preference', None)
    if preference is None:
        channels = [Notification.CHANNEL_IN_APP, Notification.CHANNEL_EMAIL]
    else:
        enabled_by_channel = {
            Notification.CHANNEL_IN_APP: preference.in_app_enabled,
            Notification.CHANNEL_EMAIL: preference.email_enabled,
            Notification.CHANNEL_SMS: preference.sms_enabled,
            Notification.CHANNEL_WHATSAPP: preference.whatsapp_enabled,
            Notification.CHANNEL_PUSH: preference.push_enabled,
        }
        channels = [channel for channel, enabled in enabled_by_channel.items() if enabled] or [Notification.CHANNEL_IN_APP]
    return notify(user, title, message, channels=channels, data=data)


def _send_in_app(user, title, message):
    return None


def _send_email(user, subject, message):
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)


def _send_sms(user, title, message):
    if not user.phone:
        raise ValueError('Utilisateur sans numéro de téléphone')
    config = settings.LMSPRO_NOTIFICATIONS
    if not config['SMS_PROVIDER_URL']:
        raise RuntimeError('SMS_PROVIDER_URL non configurée')
    requests.post(
        config['SMS_PROVIDER_URL'],
        json={'to': user.phone, 'message': message, 'api_key': config['SMS_PROVIDER_API_KEY']},
        timeout=10,
    )


def _send_whatsapp(user, title, message):
    if not user.phone:
        raise ValueError('Utilisateur sans numéro de téléphone')
    config = settings.LMSPRO_NOTIFICATIONS
    if not config['WHATSAPP_PROVIDER_URL']:
        raise RuntimeError('WHATSAPP_PROVIDER_URL non configurée')
    requests.post(
        config['WHATSAPP_PROVIDER_URL'],
        json={'to': user.phone, 'message': message},
        headers={'Authorization': f"Bearer {config['WHATSAPP_PROVIDER_TOKEN']}"},
        timeout=10,
    )


def _send_push(user, title, message):
    config = settings.LMSPRO_NOTIFICATIONS
    if not config['FCM_SERVER_KEY']:
        raise RuntimeError('FCM_SERVER_KEY non configurée')
    device_token = getattr(user, 'push_token', None)
    if not device_token:
        raise ValueError("Utilisateur sans token push enregistré")
    requests.post(
        'https://fcm.googleapis.com/fcm/send',
        json={'to': device_token, 'notification': {'title': title, 'body': message}},
        headers={'Authorization': f"key={config['FCM_SERVER_KEY']}"},
        timeout=10,
    )


_DISPATCHERS = {
    Notification.CHANNEL_IN_APP: _send_in_app,
    Notification.CHANNEL_EMAIL: _send_email,
    Notification.CHANNEL_SMS: _send_sms,
    Notification.CHANNEL_WHATSAPP: _send_whatsapp,
    Notification.CHANNEL_PUSH: _send_push,
}
