from rest_framework import serializers

from apps.social.models import Conversation, ForumPost, ForumThread, LearningGroup, MentorshipRelation, Message


class ForumPostSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)

    class Meta:
        model = ForumPost
        fields = '__all__'
        read_only_fields = ('author',)


class ForumThreadSerializer(serializers.ModelSerializer):
    posts = ForumPostSerializer(many=True, read_only=True)
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    posts_count = serializers.IntegerField(source='posts.count', read_only=True)

    class Meta:
        model = ForumThread
        fields = '__all__'
        read_only_fields = ('author', 'company')


class LearningGroupSerializer(serializers.ModelSerializer):
    members_count = serializers.IntegerField(source='members.count', read_only=True)
    is_member = serializers.SerializerMethodField()

    class Meta:
        model = LearningGroup
        fields = '__all__'
        read_only_fields = ('created_by', 'company')

    def get_is_member(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.members.filter(id=request.user.id).exists()


class MentorshipRelationSerializer(serializers.ModelSerializer):
    mentor_name = serializers.CharField(source='mentor.get_full_name', read_only=True)
    mentee_name = serializers.CharField(source='mentee.get_full_name', read_only=True)

    class Meta:
        model = MentorshipRelation
        fields = '__all__'


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)

    class Meta:
        model = Message
        fields = '__all__'
        read_only_fields = ('sender', 'read_by')


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    other_user_name = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = '__all__'

    def get_other_user_name(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        others = obj.participants.exclude(id=request.user.id)
        names = [u.get_full_name() for u in others]
        return ', '.join(names) if names else request.user.get_full_name()

    def get_last_message(self, obj):
        last = obj.messages.order_by('-created_at').first()
        return last.content if last else None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        return obj.messages.exclude(read_by=request.user).count()
