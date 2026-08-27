from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify

from apps.core.models import TimeStampedModel
from apps.core.storage import r2_media_storage


class Course(TimeStampedModel):
    LEVEL_BEGINNER = 'beginner'
    LEVEL_INTERMEDIATE = 'intermediate'
    LEVEL_ADVANCED = 'advanced'
    LEVEL_ALL = 'all_levels'
    LEVEL_CHOICES = [
        (LEVEL_BEGINNER, 'Débutant'),
        (LEVEL_INTERMEDIATE, 'Intermédiaire'),
        (LEVEL_ADVANCED, 'Avancé'),
        (LEVEL_ALL, 'Tous niveaux'),
    ]

    STATUS_DRAFT = 'draft'
    STATUS_PENDING_REVIEW = 'pending_review'
    STATUS_PUBLISHED = 'published'
    STATUS_ARCHIVED = 'archived'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Brouillon'),
        (STATUS_PENDING_REVIEW, "En attente de validation"),
        (STATUS_PUBLISHED, 'Publiée'),
        (STATUS_ARCHIVED, 'Archivée'),
    ]

    company = models.ForeignKey(
        'tenants.Company', on_delete=models.CASCADE, null=True, blank=True, related_name='courses'
    )
    category = models.ForeignKey('catalog.Category', on_delete=models.SET_NULL, null=True, related_name='courses')
    instructor = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='courses_taught')

    # Bénéficiaire du partage de revenus (admin auteur OU partenaire vidéo externe) —
    # volontairement distinct de `instructor`, qui reste le rôle pédagogique/formateur.
    # Voir apps.revenue_share pour le calcul mensuel des gains.
    revenue_partner = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='courses_revenue_share',
    )
    revenue_share_rate = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Pourcentage du revenu global du cours reversé à revenue_partner (ex: 30.00 ou 40.00)",
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    subtitle = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    thumbnail = models.ImageField(upload_to='courses/thumbnails/', null=True, blank=True)
    promo_video_url = models.URLField(blank=True)

    language = models.CharField(max_length=50, default='Français')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default=LEVEL_ALL)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_free = models.BooleanField(default=False)
    is_company_internal = models.BooleanField(
        default=False, help_text='Visible uniquement par les employés de l\'entreprise propriétaire'
    )

    requirements = models.JSONField(default=list, blank=True)
    what_you_will_learn = models.JSONField(default=list, blank=True)
    target_audience = models.TextField(blank=True)

    certificate_enabled = models.BooleanField(default=True)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_students = models.PositiveIntegerField(default=0)
    total_duration_minutes = models.PositiveIntegerField(default=0)

    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            i = 1
            while Course.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f'{base_slug}-{i}'
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class CourseSection(TimeStampedModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.course} – {self.title}'


class Chapter(TimeStampedModel):
    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE, related_name='chapters')
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.section} – {self.title}'

    @property
    def course(self):
        return self.section.course


class Lesson(TimeStampedModel):
    TYPE_VIDEO = 'video'
    TYPE_PDF = 'pdf'
    TYPE_PPT = 'ppt'
    TYPE_WORD = 'word'
    TYPE_AUDIO = 'audio'
    TYPE_IMAGE = 'image'
    TYPE_SCORM = 'scorm'
    TYPE_XAPI = 'xapi'
    TYPE_HTML5 = 'html5'
    TYPE_ZIP = 'zip'
    TYPE_TEXT = 'text'
    TYPE_CHOICES = [
        (TYPE_VIDEO, 'Vidéo'), (TYPE_PDF, 'PDF'), (TYPE_PPT, 'PowerPoint'), (TYPE_WORD, 'Word'),
        (TYPE_AUDIO, 'Audio'), (TYPE_IMAGE, 'Image'), (TYPE_SCORM, 'SCORM'), (TYPE_XAPI, 'xAPI'),
        (TYPE_HTML5, 'HTML5'), (TYPE_ZIP, 'Archive ZIP'), (TYPE_TEXT, 'Texte'),
    ]

    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    content_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_VIDEO)

    video_file = models.FileField(upload_to='courses/videos/', storage=r2_media_storage, null=True, blank=True)
    document_file = models.FileField(upload_to='courses/documents/', storage=r2_media_storage, null=True, blank=True)
    scorm_package = models.FileField(upload_to='courses/scorm/', null=True, blank=True)
    scorm_launch_url = models.CharField(max_length=500, blank=True, help_text='Résolu automatiquement depuis imsmanifest.xml')
    scorm_version = models.CharField(max_length=10, blank=True, help_text="'1.2' ou '2004', détecté depuis le manifeste")
    scorm_identifier = models.CharField(max_length=255, blank=True)
    scorm_extracted_path = models.CharField(max_length=500, blank=True, help_text='Chemin relatif sous MEDIA_ROOT du paquet décompressé')
    xapi_activity_id = models.CharField(max_length=255, blank=True)
    text_content = models.TextField(blank=True)
    external_embed_url = models.URLField(blank=True)

    duration_seconds = models.PositiveIntegerField(default=0)
    transcript = models.TextField(blank=True, help_text='§Sous-titrage automatique — transcription générée par IA')
    is_preview_free = models.BooleanField(default=False)
    download_allowed = models.BooleanField(default=False, help_text='§25.1 — interdit par défaut')
    download_window_start = models.DateTimeField(null=True, blank=True, help_text='§25.3 — téléchargement limité à une période')
    download_window_end = models.DateTimeField(null=True, blank=True)
    download_profiles = models.JSONField(
        default=list, blank=True,
        help_text="§25.3 — profils autorisés au téléchargement (ex: ['premium','company','hr']). Vide = tous les inscrits.",
    )

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'{self.chapter} – {self.title}'

    @property
    def course(self):
        return self.chapter.section.course


class LessonResource(TimeStampedModel):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='courses/resources/')
    download_allowed = models.BooleanField(default=False)
    download_window_start = models.DateTimeField(null=True, blank=True)
    download_window_end = models.DateTimeField(null=True, blank=True)
    download_profiles = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.title


class Enrollment(TimeStampedModel):
    SOURCE_PURCHASE = 'purchase'
    SOURCE_ASSIGNED = 'assigned'
    SOURCE_MANUAL = 'manual'
    SOURCE_FREE = 'free'
    SOURCE_CHOICES = [
        (SOURCE_PURCHASE, 'Achat'), (SOURCE_ASSIGNED, 'Affectation'), (SOURCE_MANUAL, 'Manuel'), (SOURCE_FREE, 'Gratuit'),
    ]

    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_DROPPED = 'dropped'
    STATUS_CHOICES = [
        (STATUS_IN_PROGRESS, 'En cours'), (STATUS_COMPLETED, 'Terminée'), (STATUS_DROPPED, 'Abandonnée'),
    ]

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    assigned_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=SOURCE_PURCHASE)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_IN_PROGRESS)
    progress_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    last_accessed_lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f'{self.user} -> {self.course} ({self.status})'


class Review(TimeStampedModel):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='course_reviews')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ('user', 'course')

    def __str__(self):
        return f'{self.course} – {self.rating}/5'


class LessonReview(TimeStampedModel):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='lesson_reviews')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ('user', 'lesson')

    def __str__(self):
        return f'{self.lesson} – {self.rating}/5'


class LessonQuestion(TimeStampedModel):
    """Per-lesson Q&A (Udemy-style), distinct from the course-level forum in apps.social."""

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='questions')
    author = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='lesson_questions')
    title = models.CharField(max_length=255)
    body = models.TextField()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class LessonAnswer(TimeStampedModel):
    question = models.ForeignKey(LessonQuestion, on_delete=models.CASCADE, related_name='answers')
    author = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='lesson_answers')
    body = models.TextField()
    is_instructor_answer = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author} – {self.question}'


class ScormRegistration(TimeStampedModel):
    """Backing store for the SCORM Run-Time Environment (RTE): the SCORM package's JS API
    wrapper (LMSGetValue/LMSSetValue/LMSCommit for 1.2, GetValue/SetValue/Commit for 2004)
    persists cmi.* values here via the registration endpoints — this is the real LMS side
    of the SCORM contract, not just a content_type label."""

    LESSON_STATUS_CHOICES = [
        ('not_attempted', 'Non commencé'), ('incomplete', 'Incomplet'), ('completed', 'Terminé'),
        ('passed', 'Réussi'), ('failed', 'Échoué'), ('browsed', 'Consulté'),
    ]

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='scorm_registrations')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='scorm_registrations')
    cmi_data = models.JSONField(default=dict, blank=True)
    lesson_status = models.CharField(max_length=20, choices=LESSON_STATUS_CHOICES, default='not_attempted')
    score_raw = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    suspend_data = models.TextField(blank=True)
    total_time_seconds = models.PositiveIntegerField(default=0)
    last_accessed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'lesson')

    def __str__(self):
        return f'{self.user} – {self.lesson} ({self.lesson_status})'


class TrainingRequest(TimeStampedModel):
    """A manager or employee requests a specific training for themselves or a team member."""

    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'En attente'),
        (STATUS_APPROVED, 'Approuvée'),
        (STATUS_REJECTED, 'Rejetée'),
    ]
    URGENCY_LOW = 'low'
    URGENCY_MEDIUM = 'medium'
    URGENCY_HIGH = 'high'
    URGENCY_CHOICES = [
        (URGENCY_LOW, 'Faible'),
        (URGENCY_MEDIUM, 'Normale'),
        (URGENCY_HIGH, 'Urgent'),
    ]

    requested_by = models.ForeignKey(
        'accounts.User', on_delete=models.CASCADE, related_name='training_requests_submitted',
    )
    for_user = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='training_requests_received',
        help_text='Si vide, la demande est pour soi-même.',
    )
    course = models.ForeignKey(
        Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='training_requests',
        help_text='Formation spécifique demandée (facultatif).',
    )
    title = models.CharField(max_length=255, blank=True, help_text='Intitulé si aucun cours existant.')
    description = models.TextField(blank=True)
    urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES, default=URGENCY_MEDIUM)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    reviewed_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )
    review_notes = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        label = self.course.title if self.course_id else (self.title or '—')
        return f'Demande "{label}" par {self.requested_by}'
