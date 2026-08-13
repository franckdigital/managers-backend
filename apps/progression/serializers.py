from rest_framework import serializers

from apps.progression.models import ChapterUnlock, ChapterValidation, CourseProgressionSettings, CourseView, LessonProgress, XAPIStatement


class CourseProgressionSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseProgressionSettings
        fields = '__all__'
        read_only_fields = ('course',)


class LessonProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonProgress
        fields = '__all__'
        read_only_fields = ('user', 'is_completed', 'completed_at')


class LessonProgressUpdateSerializer(serializers.Serializer):
    watched_seconds = serializers.IntegerField(required=False, min_value=0)
    position_seconds = serializers.IntegerField(required=False, min_value=0)
    document_viewed = serializers.BooleanField(required=False)
    time_spent_delta = serializers.IntegerField(required=False, min_value=0, default=0)
    mark_completed = serializers.BooleanField(required=False)
    # Real media duration reported by the player — backfills Lesson.duration_seconds
    # when it was left at 0 (never filled in by whoever authored the lesson), which
    # otherwise silently blocks watch-percent completion forever.
    duration_seconds = serializers.IntegerField(required=False, min_value=0)


class LessonEventSerializer(serializers.Serializer):
    VERB_CHOICES = [
        ('open',              'Ouverture de la leçon'),
        ('play',              'Lecture vidéo démarrée'),
        ('pause',             'Lecture vidéo mise en pause'),
        ('resume',            'Lecture vidéo reprise'),
        ('complete',          'Lecture vidéo terminée à 100 %'),
        ('document_view',     'Document ouvert / lu'),
        ('document_download', 'Document téléchargé'),
    ]
    verb = serializers.ChoiceField(choices=VERB_CHOICES)
    position_seconds = serializers.IntegerField(required=False, min_value=0)
    time_spent_delta = serializers.IntegerField(required=False, min_value=0, default=0)


class CourseViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseView
        fields = ['id', 'course', 'open_count', 'last_opened_at']
        read_only_fields = fields


class ChapterValidationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChapterValidation
        fields = '__all__'
        read_only_fields = ('validated_by',)


class ChapterUnlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChapterUnlock
        fields = '__all__'


class ChapterStatusSerializer(serializers.Serializer):
    chapter_id = serializers.IntegerField()
    title = serializers.CharField()
    is_unlocked = serializers.BooleanField()
    is_completed = serializers.BooleanField()


class XAPIStatementSerializer(serializers.ModelSerializer):
    class Meta:
        model = XAPIStatement
        fields = '__all__'
        read_only_fields = ('user', 'timestamp')
