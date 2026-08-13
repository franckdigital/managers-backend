from django.contrib import admin

from apps.social.models import Conversation, ForumPost, ForumThread, LearningGroup, MentorshipRelation, Message


@admin.register(ForumThread)
class ForumThreadAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'course', 'is_pinned', 'is_closed')
    list_filter = ('is_pinned', 'is_closed')


@admin.register(ForumPost)
class ForumPostAdmin(admin.ModelAdmin):
    list_display = ('thread', 'author', 'is_solution', 'created_at')


@admin.register(LearningGroup)
class LearningGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'created_by')


@admin.register(MentorshipRelation)
class MentorshipRelationAdmin(admin.ModelAdmin):
    list_display = ('mentor', 'mentee', 'status', 'started_at')
    list_filter = ('status',)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'is_group', 'title')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'sender', 'created_at')
