import secrets
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.signing import BadSignature, TimestampSigner
from django.shortcuts import redirect
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsCompanyAdmin, IsSuperAdmin
from apps.integrations.models import APIClient, ERPConnector, SSOConfiguration, WebhookEndpoint
from apps.integrations.serializers import (
    APIClientSerializer,
    ERPConnectorSerializer,
    SSOConfigurationSerializer,
    WebhookEndpointSerializer,
)
from apps.integrations.services import trigger_erp_sync

_signer = TimestampSigner()


class APIClientViewSet(viewsets.ModelViewSet):
    queryset = APIClient.objects.all()
    serializer_class = APIClientSerializer
    permission_classes = [IsCompanyAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role == 'super_admin':
            return super().get_queryset()
        return super().get_queryset().filter(company_id=user.company_id)

    def create(self, request, *args, **kwargs):
        raw_secret = secrets.token_urlsafe(32)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client = serializer.save(company=request.user.company, created_by=request.user)
        client.set_secret(raw_secret)
        client.save()
        data = self.get_serializer(client).data
        data['api_secret'] = raw_secret
        return Response(data, status=201)


class WebhookEndpointViewSet(viewsets.ModelViewSet):
    queryset = WebhookEndpoint.objects.prefetch_related('deliveries').all()
    serializer_class = WebhookEndpointSerializer
    permission_classes = [IsCompanyAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role == 'super_admin':
            return super().get_queryset()
        return super().get_queryset().filter(company_id=user.company_id)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class ERPConnectorViewSet(viewsets.ModelViewSet):
    serializer_class = ERPConnectorSerializer
    permission_classes = [IsCompanyAdmin]

    def get_queryset(self):
        return ERPConnector.objects.filter(company_id=self.request.user.company_id)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)

    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        connector = self.get_object()
        status_message = trigger_erp_sync(connector)
        return Response({'detail': status_message})


class SSOConfigurationViewSet(viewsets.ModelViewSet):
    serializer_class = SSOConfigurationSerializer
    permission_classes = [IsCompanyAdmin]

    def get_queryset(self):
        return SSOConfiguration.objects.filter(company_id=self.request.user.company_id)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.company)


class SSOLoginStartView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, company_slug):
        from apps.tenants.models import Company

        company = Company.objects.get(slug=company_slug)
        config = SSOConfiguration.objects.get(company=company, is_active=True)

        state = _signer.sign(str(config.company_id))
        params = {
            'client_id': config.client_id,
            'redirect_uri': request.build_absolute_uri('/api/integrations/sso/callback/'),
            'response_type': 'code',
            'scope': 'openid email profile',
            'state': state,
        }
        return redirect(f'{config.authorization_url}?{urlencode(params)}')


class SSOLoginCallbackView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from apps.accounts.models import User
        from apps.accounts.serializers import LmsTokenObtainPairSerializer
        from apps.core.constants import Roles

        code = request.query_params.get('code')
        state = request.query_params.get('state')
        try:
            company_id = _signer.unsign(state, max_age=600)
        except BadSignature:
            return Response({'detail': 'État SSO invalide ou expiré.'}, status=400)

        config = SSOConfiguration.objects.get(company_id=company_id)

        token_response = requests.post(config.token_url, data={
            'client_id': config.client_id,
            'client_secret': config.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': request.build_absolute_uri('/api/integrations/sso/callback/'),
        }, timeout=15).json()

        access_token = token_response.get('access_token')
        userinfo = requests.get(config.userinfo_url, headers={'Authorization': f'Bearer {access_token}'}, timeout=15).json()
        email = userinfo.get('email')
        if not email:
            return Response({'detail': "Le fournisseur SSO n'a pas renvoyé d'email."}, status=400)

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': userinfo.get('given_name', ''),
                'last_name': userinfo.get('family_name', ''),
                'company_id': company_id,
                'role': Roles.EMPLOYEE,
            },
        )

        refresh = LmsTokenObtainPairSerializer.get_token(user)
        return redirect(f'{settings.FRONTEND_BASE_URL}/sso-callback?access={refresh.access_token}&refresh={refresh}')
