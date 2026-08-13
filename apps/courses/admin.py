from django.contrib import admin

from apps.courses.models import Chapter, Course, CourseSection, Enrollment, Lesson, LessonResource, Review


class CourseSectionInline(admin.TabularInline):
    model = CourseSection
    extra = 0


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'instructor', 'status', 'level', 'price', 'total_students', 'average_rating')
    list_filter = ('status', 'level', 'is_free', 'is_company_internal')
    search_fields = ('title', 'subtitle')
    inlines = [CourseSectionInline]


class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0


@admin.register(CourseSection)
class CourseSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    inlines = [ChapterInline]


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ('title', 'section', 'order')
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'chapter', 'content_type', 'order', 'download_allowed')
    list_filter = ('content_type', 'download_allowed')


@admin.register(LessonResource)
class LessonResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'lesson', 'download_allowed')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'status', 'source', 'progress_percent', 'enrolled_at')
    list_filter = ('status', 'source')
    search_fields = ('user__email', 'course__title')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'rating')
