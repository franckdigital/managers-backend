from django.conf import settings
from django.urls import reverse


class PaymentInitResult:
    def __init__(self, provider_reference, redirect_url=None, client_secret=None, raw=None):
        self.provider_reference = provider_reference
        self.redirect_url = redirect_url
        self.client_secret = client_secret
        self.raw = raw or {}


class BasePaymentProvider:
    code = None

    def init_payment(self, order):
        raise NotImplementedError

    def verify_payment(self, provider_reference):
        raise NotImplementedError


class ManualProvider(BasePaymentProvider):
    """Marks the payment as instantly succeeded. Used for free enrollments, admin-granted
    access and as a safe default when no real payment gateway is configured yet."""

    code = 'manual'

    def init_payment(self, order):
        return PaymentInitResult(provider_reference=f'MANUAL-{order.id}', raw={'mode': 'manual'})

    def verify_payment(self, provider_reference):
        return {'status': 'succeeded', 'reference': provider_reference}


class CashProvider(BasePaymentProvider):
    """Cash payment — creates a pending payment record. Admin must validate after
    verifying the physical receipt/proof uploaded by the learner."""

    code = 'cash'

    def init_payment(self, order):
        return PaymentInitResult(provider_reference=f'CASH-{order.id}', raw={'mode': 'cash', 'status': 'pending_validation'})

    def verify_payment(self, provider_reference):
        return {'status': 'pending', 'reference': provider_reference}


class StripeProvider(BasePaymentProvider):
    code = 'stripe'

    def _client(self):
        import stripe

        stripe.api_key = settings.LMSPRO_PAYMENT_PROVIDERS['STRIPE_SECRET_KEY']
        if not stripe.api_key:
            raise RuntimeError('STRIPE_SECRET_KEY non configurée')
        return stripe

    def init_payment(self, order):
        stripe = self._client()
        intent = stripe.PaymentIntent.create(
            amount=int(order.total_amount * 100),
            currency=order.currency.lower(),
            metadata={'order_id': str(order.id)},
        )
        return PaymentInitResult(provider_reference=intent.id, client_secret=intent.client_secret, raw=intent)

    def verify_payment(self, provider_reference):
        stripe = self._client()
        intent = stripe.PaymentIntent.retrieve(provider_reference)
        return {'status': 'succeeded' if intent.status == 'succeeded' else intent.status, 'raw': intent}


class CinetPayProvider(BasePaymentProvider):
    """Covers card payments + West-African mobile money (Orange/MTN/Moov/Wave) via the
    CinetPay aggregator, as listed in the cahier des charges §20."""

    code = 'cinetpay'
    BASE_URL = 'https://api-checkout.cinetpay.com/v2'

    def init_payment(self, order):
        import logging
        import uuid
        import requests

        logger = logging.getLogger(__name__)
        config = settings.LMSPRO_PAYMENT_PROVIDERS
        if not config['CINETPAY_API_KEY']:
            raise RuntimeError('CINETPAY_API_KEY non configurée')

        transaction_id = f'LMS-{uuid.uuid4().hex[:10].upper()}'

        # Skip the real API call when CINETPAY_MOCK is enabled (dev or staging)
        if getattr(settings, 'CINETPAY_MOCK', False):
            mock_url = f'{settings.FRONTEND_BASE_URL}/checkout/cinetpay-mock?tid={transaction_id}&order={order.id}'
            logger.warning('CinetPay MOCK — returning fake payment URL: %s', mock_url)
            return PaymentInitResult(
                provider_reference=transaction_id,
                redirect_url=mock_url,
                raw={'mock': True, 'transaction_id': transaction_id},
            )

        customer_name = order.user.get_full_name() or order.user.email
        notify_url = f'{settings.BACKEND_BASE_URL}{reverse("cinetpay-webhook")}'
        payload = {
            'apikey': config['CINETPAY_API_KEY'],
            'site_id': config['CINETPAY_SITE_ID'],
            'transaction_id': transaction_id,
            'amount': float(order.total_amount),
            'currency': order.currency,
            'description': f'Abonnement LMS PRO #{order.id}',
            'customer_name': customer_name,
            'customer_email': order.user.email,
            'notify_url': notify_url,
            'return_url': f'{settings.FRONTEND_BASE_URL}/checkout/success',
            'channels': 'ALL',
            'metadata': transaction_id,
        }

        try:
            response = requests.post(f'{self.BASE_URL}/payment', json=payload, timeout=30)
            raw_text = response.text
            logger.info('CinetPay HTTP %s — %.500s', response.status_code, raw_text)
            if not raw_text:
                raise RuntimeError('CinetPay: réponse vide')
            data = response.json()
        except requests.exceptions.Timeout:
            raise RuntimeError("CinetPay: délai d'attente dépassé")
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f'CinetPay: erreur réseau — {exc}')
        except ValueError:
            raise RuntimeError('CinetPay: réponse invalide (non-JSON)')

        if str(data.get('code', '')) != '201':
            msg = data.get('message') or data.get('description') or 'Erreur CinetPay'
            raise RuntimeError(f'CinetPay: {msg} (code={data.get("code")})')

        return PaymentInitResult(
            provider_reference=transaction_id,
            redirect_url=data.get('data', {}).get('payment_url'),
            raw=data,
        )

    def verify_payment(self, provider_reference):
        import requests

        config = settings.LMSPRO_PAYMENT_PROVIDERS
        payload = {
            'apikey': config['CINETPAY_API_KEY'],
            'site_id': config['CINETPAY_SITE_ID'],
            'transaction_id': provider_reference,
        }
        response = requests.post(f'{self.BASE_URL}/payment/check', json=payload, timeout=15)
        data = response.json()
        status = 'succeeded' if data.get('data', {}).get('status') == 'ACCEPTED' else data.get('data', {}).get('status')
        return {'status': status, 'raw': data}


class PayPalProvider(BasePaymentProvider):
    code = 'paypal'

    @property
    def base_url(self):
        mode = settings.LMSPRO_PAYMENT_PROVIDERS['PAYPAL_MODE']
        return 'https://api-m.paypal.com' if mode == 'live' else 'https://api-m.sandbox.paypal.com'

    def _access_token(self):
        import requests

        config = settings.LMSPRO_PAYMENT_PROVIDERS
        if not config['PAYPAL_CLIENT_ID'] or not config['PAYPAL_CLIENT_SECRET']:
            raise RuntimeError('PAYPAL_CLIENT_ID/PAYPAL_CLIENT_SECRET non configurés')

        response = requests.post(
            f'{self.base_url}/v1/oauth2/token',
            auth=(config['PAYPAL_CLIENT_ID'], config['PAYPAL_CLIENT_SECRET']),
            data={'grant_type': 'client_credentials'},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()['access_token']

    def init_payment(self, order):
        import requests

        token = self._access_token()
        payload = {
            'intent': 'CAPTURE',
            'purchase_units': [{
                'reference_id': str(order.id),
                'amount': {'currency_code': order.currency, 'value': f'{order.total_amount:.2f}'},
            }],
            'application_context': {
                'return_url': f'{settings.FRONTEND_BASE_URL}/checkout/success',
                'cancel_url': f'{settings.FRONTEND_BASE_URL}/checkout/cancel',
            },
        }
        response = requests.post(
            f'{self.base_url}/v2/checkout/orders',
            json=payload,
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            timeout=15,
        )
        data = response.json()
        approve_link = next((link['href'] for link in data.get('links', []) if link['rel'] == 'approve'), None)
        return PaymentInitResult(provider_reference=data.get('id'), redirect_url=approve_link, raw=data)

    def verify_payment(self, provider_reference):
        import requests

        token = self._access_token()
        response = requests.post(
            f'{self.base_url}/v2/checkout/orders/{provider_reference}/capture',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            timeout=15,
        )
        data = response.json()
        status = 'succeeded' if data.get('status') == 'COMPLETED' else data.get('status')
        return {'status': status, 'raw': data}


_PROVIDERS = {
    ManualProvider.code: ManualProvider,
    CashProvider.code: CashProvider,
    StripeProvider.code: StripeProvider,
    CinetPayProvider.code: CinetPayProvider,
    PayPalProvider.code: PayPalProvider,
}


def get_provider(code):
    provider_class = _PROVIDERS.get(code)
    if provider_class is None:
        raise ValueError(f'Fournisseur de paiement inconnu: {code}')
    return provider_class()
