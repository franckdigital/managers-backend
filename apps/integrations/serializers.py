from rest_framework import serializers

from apps.integrations.models import APIClient, ERPConnector, SSOConfiguration, WebhookDelivery, WebhookEndpoint


class APIClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = APIClient
        fields = '__all__'
        read_only_fields = ('api_key', 'api_secret_hash', 'created_by')


class WebhookDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDelivery
        fields = '__all__'


class WebhookEndpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEndpoint
        fields = '__all__'
        read_only_fields = ('secret',)


class ERPConnectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ERPConnector
        fields = '__all__'
        read_only_fields = ('last_sync_at', 'last_sync_status')


class SSOConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SSOConfiguration
        fields = '__all__'
        extra_kwargs = {'client_secret': {'write_only': True}}
