from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel


class Skill(TimeStampedModel):
    company = models.ForeignKey('tenants.Company', on_delete=models.CASCADE, null=True, blank=True, related_name='skills')
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=120, blank=True)

    class Meta:
        unique_together = ('company', 'name')

    def __str__(self):
        return self.name


class CourseSkill(TimeStampedModel):
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='skills')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='courses')
    level_gained = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(5)])

    class Meta:
        unique_together = ('course', 'skill')


class JobRole(TimeStampedModel):
    company = models.ForeignKey('tenants.Company', on_delete=models.CASCADE, null=True, blank=True, related_name='job_roles')
    title = models.CharField(max_length=150)

    def __str__(self):
        return self.title


class JobRoleSkillRequirement(TimeStampedModel):
    job_role = models.ForeignKey(JobRole, on_delete=models.CASCADE, related_name='skill_requirements')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='job_requirements')
    required_level = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])

    class Meta:
        unique_together = ('job_role', 'skill')


class EmployeeSkill(TimeStampedModel):
    SOURCE_SELF = 'self_assessment'
    SOURCE_MANAGER = 'manager'
    SOURCE_AUTO = 'auto_computed'
    SOURCE_CHOICES = [
        (SOURCE_SELF, 'Auto-évaluation'), (SOURCE_MANAGER, 'Manager'), (SOURCE_AUTO, 'Calcul automatique'),
    ]

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='skill_levels')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='employee_levels')
    level = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_AUTO)
    last_assessed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'skill')


class IndividualDevelopmentPlan(TimeStampedModel):
    STATUS_DRAFT = 'draft'
    STATUS_ACTIVE = 'active'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES = [(STATUS_DRAFT, 'Brouillon'), (STATUS_ACTIVE, 'Actif'), (STATUS_COMPLETED, 'Terminé')]

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='development_plans')
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='+')
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    def __str__(self):
        return f'PDI {self.user} ({self.period_start} – {self.period_end})'


class PDIObjective(TimeStampedModel):
    STATUS_NOT_STARTED = 'not_started'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_ACHIEVED = 'achieved'
    STATUS_CHOICES = [
        (STATUS_NOT_STARTED, 'Non démarré'), (STATUS_IN_PROGRESS, 'En cours'), (STATUS_ACHIEVED, 'Atteint'),
    ]

    plan = models.ForeignKey(IndividualDevelopmentPlan, on_delete=models.CASCADE, related_name='objectives')
    skill = models.ForeignKey(Skill, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    course = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    description = models.TextField()
    target_date = models.DateField(null=True, blank=True)
    expected_result = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_NOT_STARTED)


class Evaluation360Campaign(TimeStampedModel):
    STATUS_OPEN = 'open'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [(STATUS_OPEN, 'Ouverte'), (STATUS_CLOSED, 'Clôturée')]

    company = models.ForeignKey('tenants.Company', on_delete=models.CASCADE, related_name='evaluation_campaigns')
    target_user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='evaluation_360s')
    title = models.CharField(max_length=255)
    period_start = models.DateField()
    period_end = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_OPEN)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='+')

    def __str__(self):
        return f'{self.title} – {self.target_user}'


class Evaluation360Response(TimeStampedModel):
    EVALUATOR_SELF = 'self'
    EVALUATOR_MANAGER = 'manager'
    EVALUATOR_PEER = 'peer'
    EVALUATOR_HR = 'hr'
    EVALUATOR_FINAL = 'final'
    EVALUATOR_CHOICES = [
        (EVALUATOR_SELF, 'Auto-évaluation'), (EVALUATOR_MANAGER, 'Manager'),
        (EVALUATOR_PEER, 'Collègue'), (EVALUATOR_HR, 'RH'),
        (EVALUATOR_FINAL, 'Évaluation finale'),
    ]

    campaign = models.ForeignKey(Evaluation360Campaign, on_delete=models.CASCADE, related_name='responses')
    evaluator = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='+')
    evaluator_type = models.CharField(max_length=10, choices=EVALUATOR_CHOICES)
    answers = models.JSONField(default=dict, blank=True)
    overall_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('campaign', 'evaluator', 'evaluator_type')


class TrainingBudgetEntry(TimeStampedModel):
    company = models.ForeignKey('tenants.Company', on_delete=models.CASCADE, related_name='training_budgets')
    year = models.PositiveIntegerField()
    amount_allocated = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    amount_spent = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ('company', 'year')

    def __str__(self):
        return f'{self.company} – {self.year}'
