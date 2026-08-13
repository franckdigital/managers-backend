import hashlib
import hmac
import json

import requests
from django.utils import timezone

from apps.integrations.models import WebhookDelivery, WebhookEndpoint


def send_webhook(event_type, company, payload):
    if company is None:
        return []

    deliveries = []
    for endpoint in WebhookEndpoint.objects.filter(is_active=True, company=company):
        if event_type in endpoint.events:
            deliveries.append(_deliver(endpoint, event_type, payload))
    return deliveries


def _deliver(endpoint, event_type, payload):
    body = json.dumps({'event': event_type, 'data': payload}, default=str)
    signature = hmac.new(endpoint.secret.encode(), body.encode(), hashlib.sha256).hexdigest()

    delivery = WebhookDelivery.objects.create(endpoint=endpoint, event_type=event_type, payload=payload, attempt_count=1)
    try:
        response = requests.post(
            endpoint.url,
            data=body,
            headers={'Content-Type': 'application/json', 'X-LMSPRO-Signature': signature},
            timeout=10,
        )
        delivery.response_status = response.status_code
        delivery.response_body = response.text[:2000]
        delivery.success = response.ok
    except requests.RequestException as exc:
        delivery.response_body = str(exc)
        delivery.success = False

    delivery.delivered_at = timezone.now()
    delivery.save()
    return delivery


REQUIRED_ERP_FIELDS = {
    'sage': ['sync_endpoint', 'api_key'],
    'odoo': ['url', 'db', 'username', 'api_key'],
    'sap': ['sync_endpoint', 'client_id', 'client_secret'],
    'oracle': ['sync_endpoint', 'client_id', 'client_secret'],
    'workday': ['sync_endpoint', 'client_id', 'client_secret'],
}


def trigger_erp_sync(connector):
    """Pushes completed-training records to the configured ERP/HRIS. Odoo gets a real
    XML-RPC sync (its external API is a stable, documented protocol). The other providers
    (Sage/SAP/Oracle/Workday) get a real outbound HTTPS push to the customer's configured
    middleware endpoint — those vendors' proprietary REST contracts differ per tenant/module
    setup, so the integration point is a customer-supplied `sync_endpoint`, not a guessed path."""

    missing = [field for field in REQUIRED_ERP_FIELDS.get(connector.provider, []) if not connector.config.get(field)]
    if missing:
        return _record_sync_result(connector, False, f"Configuration incomplète, champs manquants: {', '.join(missing)}")

    if connector.provider == 'odoo':
        return _sync_odoo(connector)
    return _sync_generic_rest(connector)


def _completed_trainings_payload(connector):
    from datetime import timedelta

    from apps.courses.models import Enrollment

    since = connector.last_sync_at or (timezone.now() - timedelta(days=30))
    enrollments = Enrollment.objects.filter(
        user__company=connector.company, status=Enrollment.STATUS_COMPLETED, completed_at__gte=since,
    ).select_related('user', 'course')
    return [
        {
            'user_email': enrollment.user.email,
            'user_full_name': enrollment.user.get_full_name(),
            'employee_id': enrollment.user.employee_id,
            'course_title': enrollment.course.title if enrollment.course else '',
            'completed_at': enrollment.completed_at.isoformat(),
        }
        for enrollment in enrollments
    ]


def _sync_odoo(connector):
    import xmlrpc.client

    config = connector.config
    payload = _completed_trainings_payload(connector)
    try:
        common = xmlrpc.client.ServerProxy(f"{config['url']}/xmlrpc/2/common")
        uid = common.authenticate(config['db'], config['username'], config['api_key'], {})
        if not uid:
            return _record_sync_result(connector, False, 'Authentification Odoo refusée (identifiants invalides).')

        models_proxy = xmlrpc.client.ServerProxy(f"{config['url']}/xmlrpc/2/object")
        for record in payload:
            employee_ids = models_proxy.execute_kw(
                config['db'], uid, config['api_key'], 'hr.employee', 'search',
                [[['work_email', '=', record['user_email']]]],
            )
            if employee_ids:
                models_proxy.execute_kw(
                    config['db'], uid, config['api_key'], 'hr.employee', 'message_post',
                    [employee_ids[:1]],
                    {'body': f"Formation terminée : {record['course_title']} le {record['completed_at']}"},
                )
        return _record_sync_result(connector, True, f'{len(payload)} formation(s) synchronisée(s) vers Odoo.')
    except Exception as exc:
        return _record_sync_result(connector, False, f'Échec de synchronisation Odoo: {exc}')


def _sync_generic_rest(connector):
    config = connector.config
    endpoint = config['sync_endpoint']
    payload = _completed_trainings_payload(connector)
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f"Bearer {config.get('api_key') or config.get('client_secret')}",
    }

    try:
        response = requests.post(endpoint, json={'trainings': payload}, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        return _record_sync_result(connector, False, f"Échec de l'appel vers {connector.provider}: {exc}")

    return _record_sync_result(connector, True, f'{len(payload)} formation(s) transmise(s) à {connector.provider}.')


def _record_sync_result(connector, success, message):
    connector.last_sync_at = timezone.now()
    connector.last_sync_status = message[:255]
    connector.save(update_fields=['last_sync_at', 'last_sync_status'])
    return connector.last_sync_status
