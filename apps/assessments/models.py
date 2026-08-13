from django.db import models

from apps.core.models import TimeStampedModel


class QuestionBank(TimeStampedModel):
    company = models.ForeignKey('tenants.Company', on_delete=models.CASCADE, null=True, blank=True, related_name='question_banks')
    title = models.CharField(max_length=255)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='+')

    def __str__(self):
        return self.title


class Question(TimeStampedModel):
    TYPE_MCQ = 'mcq'
    TYPE_TRUE_FALSE = 'true_false'
    TYPE_OPEN_TEXT = 'open_text'
    TYPE_MATCHING = 'matching'
    TYPE_DRAG_DROP = 'drag_drop'
    TYPE_CHOICES = [
        (TYPE_MCQ, 'QCM'), (TYPE_TRUE_FALSE, 'Vrai/Faux'), (TYPE_OPEN_TEXT, 'Texte libre'),
        (TYPE_MATCHING, 'Association'), (TYPE_DRAG_DROP, 'Glisser-déposer'),
    ]

    DIFFICULTY_EASY = 'easy'
    DIFFICULTY_MEDIUM = 'medium'
    DIFFICULTY_HARD = 'hard'
    DIFFICULTY_CHOICES = [(DIFFICULTY_EASY, 'Facile'), (DIFFICULTY_MEDIUM, 'Moyen'), (DIFFICULTY_HARD, 'Difficile')]

    bank = models.ForeignKey(QuestionBank, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    question_type = models.CharField(max_length=12, choices=TYPE_CHOICES, default=TYPE_MCQ)
    is_multiple_answer = models.BooleanField(default=False)
    points = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    explanation = models.TextField(blank=True)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default=DIFFICULTY_MEDIUM)
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.text[:80]


class QuestionChoice(TimeStampedModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.text


class Assessment(TimeStampedModel):
    TYPE_QUIZ = 'quiz'
    TYPE_EXAM = 'exam'
    TYPE_ASSIGNMENT = 'assignment'
    TYPE_CHOICES = [(TYPE_QUIZ, 'Quiz'), (TYPE_EXAM, 'Examen'), (TYPE_ASSIGNMENT, 'Devoir / Cas pratique')]

    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='assessments')
    chapter = models.ForeignKey(
        'courses.Chapter', on_delete=models.CASCADE, null=True, blank=True, related_name='assessments',
        help_text='Vide = évaluation au niveau de la formation entière (examen final)',
    )
    title = models.CharField(max_length=255)
    assessment_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_QUIZ)
    instructions = models.TextField(blank=True)

    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True)
    max_attempts = models.PositiveIntegerField(default=1)
    passing_score = models.DecimalField(max_digits=5, decimal_places=2, default=70)

    is_randomized = models.BooleanField(default=False)
    question_pool_size = models.PositiveIntegerField(null=True, blank=True)
    question_bank = models.ForeignKey(QuestionBank, on_delete=models.SET_NULL, null=True, blank=True, related_name='assessments')
    shuffle_choices = models.BooleanField(default=True)
    anti_cheat_enabled = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class AssessmentQuestion(TimeStampedModel):
    """Fixed question list, used when is_randomized=False."""

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='assessment_questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='+')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        unique_together = ('assessment', 'question')


class AssessmentAttempt(TimeStampedModel):
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_SUBMITTED = 'submitted'
    STATUS_GRADED = 'graded'
    STATUS_EXPIRED = 'expired'
    STATUS_CHOICES = [
        (STATUS_IN_PROGRESS, 'En cours'), (STATUS_SUBMITTED, 'Soumise'),
        (STATUS_GRADED, 'Notée'), (STATUS_EXPIRED, 'Expirée'),
    ]

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='attempts')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='assessment_attempts')
    attempt_number = models.PositiveIntegerField(default=1)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_passed = models.BooleanField(null=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_IN_PROGRESS)
    proctoring_flags = models.JSONField(default=list, blank=True)
    questions_snapshot = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.user} – {self.assessment} (#{self.attempt_number})'


class AttemptAnswer(TimeStampedModel):
    attempt = models.ForeignKey(AssessmentAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='+')
    selected_choices = models.ManyToManyField(QuestionChoice, blank=True, related_name='+')
    text_answer = models.TextField(blank=True)
    matching_answer = models.JSONField(default=dict, blank=True)
    is_correct = models.BooleanField(null=True)
    points_awarded = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        unique_together = ('attempt', 'question')


class AssignmentSubmission(TimeStampedModel):
    attempt = models.OneToOneField(AssessmentAttempt, on_delete=models.CASCADE, related_name='assignment_submission')
    file = models.FileField(upload_to='assignments/submissions/', null=True, blank=True)
    comment = models.TextField(blank=True)
    grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True)
    graded_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    graded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Devoir de {self.attempt.user}'
