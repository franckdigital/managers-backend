from django.db import models

from apps.core.models import TimeStampedModel


class ForumThread(TimeStampedModel):
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, null=True, blank=True, related_name='forum_threads')
    company = models.ForeignKey('tenants.Company', on_delete=models.CASCADE, null=True, blank=True, related_name='forum_threads')
    author = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='forum_threads')
    title = models.CharField(max_length=255)
    is_pinned = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return self.title


class ForumPost(TimeStampedModel):
    thread = models.ForeignKey(ForumThread, on_delete=models.CASCADE, related_name='posts')
    author = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='forum_posts')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    content = models.TextField()
    is_solution = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author} – {self.thread}'


class LearningGroup(TimeStampedModel):
    company = models.ForeignKey('tenants.Company', on_delete=models.CASCADE, null=True, blank=True, related_name='learning_groups')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    members = models.ManyToManyField('accounts.User', blank=True, related_name='learning_groups')
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='+')

    def __str__(self):
        return self.name


class MentorshipRelation(TimeStampedModel):
    STATUS_PENDING = 'pending'
    STATUS_ACTIVE = 'active'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES = [(STATUS_PENDING, 'En attente'), (STATUS_ACTIVE, 'Active'), (STATUS_COMPLETED, 'Terminée')]

    mentor = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='mentees')
    mentee = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='mentors')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    started_at = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ('mentor', 'mentee')


class Conversation(TimeStampedModel):
    participants = models.ManyToManyField('accounts.User', related_name='conversations')
    is_group = models.BooleanField(default=False)
    title = models.CharField(max_length=255, blank=True)


class Message(TimeStampedModel):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    read_by = models.ManyToManyField('accounts.User', blank=True, related_name='read_messages')

    class Meta:
        ordering = ['created_at']
