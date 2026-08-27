from rest_framework import serializers

from apps.revenue_share.models import PartnerMonthlyEarning, PartnerPayout, PartnerPayoutItem


class PartnerMonthlyEarningSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    partner_name = serializers.CharField(source='partner.get_full_name', read_only=True)

    class Meta:
        model = PartnerMonthlyEarning
        fields = '__all__'


class PartnerPayoutItemSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='earning.course.title', read_only=True)
    year = serializers.IntegerField(source='earning.year', read_only=True)
    month = serializers.IntegerField(source='earning.month', read_only=True)

    class Meta:
        model = PartnerPayoutItem
        fields = '__all__'


class PartnerPayoutSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source='partner.get_full_name', read_only=True)
    items = PartnerPayoutItemSerializer(many=True, read_only=True)

    class Meta:
        model = PartnerPayout
        fields = '__all__'
        read_only_fields = ('partner', 'gross_amount', 'status', 'processed_by', 'processed_at')
