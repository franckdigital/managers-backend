from rest_framework import serializers

from apps.courses.models import (
    Chapter,
    Course,
    CourseSection,
    Enrollment,
    Lesson,
    LessonAnswer,
    LessonQuestion,
    LessonResource,
    LessonReview,
    Review,
    ScormRegistration,
    TrainingRequest,
)


class LessonResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonResource
        fields = '__all__'


class ScormRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScormRegistration
        fields = '__all__'
        read_only_fields = ('user', 'lesson', 'last_accessed_at')


class ScormCommitSerializer(serializers.Serializer):
    cmi = serializers.DictField()


class LessonSerializer(serializers.ModelSerializer):
    """`video_file_key`/`document_file_key` attach a file already uploaded straight to
    R2 via the presign-upload flow — the object exists in the bucket already, this just
    points the FileField at it (no bytes pass through this serializer)."""

    resources = LessonResourceSerializer(many=True, read_only=True)
    video_file_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    document_file_key = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Lesson
        fields = '__all__'

    def _attach_direct_upload_keys(self, instance, video_key, document_key):
        if video_key:
            instance.video_file.name = video_key
        if document_key:
            instance.document_file.name = document_key
        if video_key or document_key:
            instance.save()

    def create(self, validated_data):
        video_key = validated_data.pop('video_file_key', None)
        document_key = validated_data.pop('document_file_key', None)
        instance = super().create(validated_data)
        self._attach_direct_upload_keys(instance, video_key, document_key)
        return instance

    def update(self, instance, validated_data):
        video_key = validated_data.pop('video_file_key', None)
        document_key = validated_data.pop('document_file_key', None)
        instance = super().update(instance, validated_data)
        self._attach_direct_upload_keys(instance, video_key, document_key)
        return instance


class LessonLightSerializer(serializers.ModelSerializer):
    """Used for nested listing without exposing raw file URLs (DRM: streaming goes through content_security)."""

    class Meta:
        model = Lesson
        fields = ('id', 'title', 'order', 'content_type', 'duration_seconds', 'is_preview_free')


class LessonResourceLightSerializer(serializers.ModelSerializer):
    """Resource metadata for learners — the raw `file` URL is never exposed; access goes
    through content_security's resource ticket/streaming endpoints (§25)."""

    class Meta:
        model = LessonResource
        fields = ('id', 'title', 'download_allowed')


class LessonPlayerSerializer(serializers.ModelSerializer):
    """Learner-facing lesson detail — deliberately excludes video_file/document_file/
    scorm_package (raw URLs would bypass the secure-streaming/DRM layer in content_security)."""

    resources = LessonResourceLightSerializer(many=True, read_only=True)
    has_media = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = (
            'id', 'chapter', 'title', 'order', 'content_type', 'text_content', 'transcript',
            'duration_seconds', 'is_preview_free', 'external_embed_url', 'resources', 'has_media',
        )

    def get_has_media(self, obj):
        return bool(obj.video_file or obj.document_file or obj.scorm_package)


class ChapterSerializer(serializers.ModelSerializer):
    lessons = LessonLightSerializer(many=True, read_only=True)

    class Meta:
        model = Chapter
        fields = '__all__'


class CourseSectionSerializer(serializers.ModelSerializer):
    chapters = ChapterSerializer(many=True, read_only=True)

    class Meta:
        model = CourseSection
        fields = '__all__'


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = Review
        fields = '__all__'
        read_only_fields = ('user',)


class LessonReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)

    class Meta:
        model = LessonReview
        fields = '__all__'
        read_only_fields = ('user',)


class CourseListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    instructor_name = serializers.CharField(source='instructor.get_full_name', read_only=True)

    class Meta:
        model = Course
        fields = (
            'id', 'title', 'slug', 'subtitle', 'thumbnail', 'category', 'category_name', 'instructor',
            'instructor_name', 'level', 'status', 'price', 'is_free', 'is_company_internal', 'average_rating',
            'total_students', 'total_duration_minutes', 'company',
        )


class CourseDetailSerializer(serializers.ModelSerializer):
    sections = CourseSectionSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    # Learners rate/comment per lesson (LessonReview), not the course as a whole
    # (Review) — the course page only ever showed the latter, so per-lesson feedback
    # never surfaced here even though that's the review flow actually in use.
    lesson_reviews = serializers.SerializerMethodField()
    instructor_name = serializers.CharField(source='instructor.get_full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    revenue_partner_name = serializers.CharField(source='revenue_partner.get_full_name', read_only=True, default=None)

    class Meta:
        model = Course
        fields = '__all__'
        read_only_fields = ('slug', 'average_rating', 'total_students')

    def get_lesson_reviews(self, obj):
        qs = LessonReview.objects.filter(
            lesson__chapter__section__course=obj
        ).select_related('user', 'lesson').order_by('-created_at')
        return LessonReviewSerializer(qs, many=True).data


class EnrollmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_thumbnail = serializers.ImageField(source='course.thumbnail', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = Enrollment
        fields = '__all__'
        read_only_fields = ('user', 'progress_percent', 'status', 'completed_at', 'enrolled_at')


class LessonAnswerSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)

    class Meta:
        model = LessonAnswer
        fields = '__all__'
        read_only_fields = ('author', 'is_instructor_answer')


class LessonQuestionSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    answers = LessonAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = LessonQuestion
        fields = '__all__'
        read_only_fields = ('author',)


class AssignCourseSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    course_id = serializers.IntegerField()
    due_date = serializers.DateField(required=False, allow_null=True)


class TrainingRequestSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.SerializerMethodField(read_only=True)
    for_user_name = serializers.SerializerMethodField(read_only=True)
    course_title = serializers.SerializerMethodField(read_only=True)
    reviewed_by_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TrainingRequest
        fields = '__all__'
        read_only_fields = ('requested_by', 'reviewed_by', 'reviewed_at', 'status')

    def get_requested_by_name(self, obj):
        return obj.requested_by.get_full_name() or obj.requested_by.email

    def get_for_user_name(self, obj):
        if obj.for_user:
            return obj.for_user.get_full_name() or obj.for_user.email
        return None

    def get_course_title(self, obj):
        return obj.course.title if obj.course_id else None

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.get_full_name() or obj.reviewed_by.email
        return None
