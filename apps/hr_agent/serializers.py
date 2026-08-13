from rest_framework import serializers

from apps.hr_agent.models import AgentConversation, AgentMessage, AgentResource, JobDescriptionRequest


class AgentResourceSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True, default=None)
    service_name = serializers.CharField(source='service.name', read_only=True, default=None)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = AgentResource
        fields = [
            'id', 'company', 'department', 'department_name', 'service', 'service_name',
            'category', 'content_type', 'title', 'text_body', 'file', 'file_url', 'video_url',
            'keywords', 'order', 'is_active', 'created_at',
        ]
        read_only_fields = ('created_by',)

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url


class AgentMessageSerializer(serializers.ModelSerializer):
    resources = AgentResourceSerializer(many=True, read_only=True)

    class Meta:
        model = AgentMessage
        fields = ['id', 'role', 'content', 'intent', 'resources', 'created_at']


class AgentConversationSerializer(serializers.ModelSerializer):
    messages = AgentMessageSerializer(many=True, read_only=True)

    class Meta:
        model = AgentConversation
        fields = ['id', 'created_at', 'updated_at', 'messages']


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(allow_blank=False)


class JobDescriptionRequestSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    job_title = serializers.CharField(max_length=255)
    department_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    manager_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    missions = serializers.ListField(child=serializers.CharField(max_length=300), required=False, default=list)


class JobDescriptionResultSerializer(serializers.ModelSerializer):
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = JobDescriptionRequest
        fields = [
            'id', 'full_name', 'job_title', 'department_name', 'manager_name',
            'start_date', 'missions', 'pdf_url', 'created_at',
        ]

    def get_pdf_url(self, obj):
        if not obj.pdf_file:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(obj.pdf_file.url) if request else obj.pdf_file.url
