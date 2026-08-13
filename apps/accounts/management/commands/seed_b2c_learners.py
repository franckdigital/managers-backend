"""
Management command: seed_b2c_learners
Creates 20 B2C learners (company=null, role=student) with:
  - Enrollment in published B2C courses
  - LessonProgress (mixed completion profiles)
  - AssessmentAttempts (graded)
  - Platform-wide Skills (company=null)
  - EmployeeSkills
  - IndividualDevelopmentPlans + PDIObjectives

Usage:
    python manage.py seed_b2c_learners
    python manage.py seed_b2c_learners --reset
"""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


def _past(n): return timezone.now() - timedelta(days=n)
def _date_past(n): return date.today() - timedelta(days=n)
def _date_future(n): return date.today() + timedelta(days=n)


LEARNER_NAMES = [
    ('Aminata',    'Diallo',       'CI'), ('Kwame',     'Asante',      'GH'),
    ('Fatima',     'Coulibaly',    'SN'), ('Jean-Pierre','Mensah',     'TG'),
    ('Aissatou',   'Traoré',       'ML'), ('Moussa',    'Konaté',      'CI'),
    ('Naomi',      'Agyei',        'GH'), ('Ibrahim',   'Bah',         'SN'),
    ('Cécile',     'Ouédraogo',    'BF'), ('Théodore',  'Koffi',       'CI'),
    ('Rokhaya',    'Sarr',         'SN'), ('Emmanuel',  'Tetteh',      'GH'),
    ('Mariama',    'Sow',          'SN'), ('Patrick',   'Adeyemi',     'CM'),
    ('Adjoa',      'Acheampong',   'GH'), ('Oumar',     'Dieng',       'SN'),
    ('Clarisse',   'Nkemdirim',    'CM'), ('Serge',     'Gnagne',      'CI'),
    ('Hawa',       'Barry',        'ML'), ('David',     'Osei',        'GH'),
]

COUNTRY_LABELS = {
    'CI': "Côte d'Ivoire", 'GH': 'Ghana', 'SN': 'Sénégal', 'TG': 'Togo',
    'ML': 'Mali', 'BF': 'Burkina Faso', 'CM': 'Cameroun',
}

PLATFORM_SKILLS = [
    ('Python & Data Science',          'Technique'),
    ('Communication Professionnelle',   'Soft Skills'),
    ('Excel & Analyse de Données',      'Technique'),
    ('Leadership & Management',         'Management'),
    ('Comptabilité de Base',            'Finance'),
    ('Gestion de Projet',               'Management'),
    ('Marketing Digital',               'Marketing'),
    ('SQL & Bases de Données',          'Technique'),
    ('Cybersécurité',                   'Technique'),
    ('Anglais des Affaires',            'Soft Skills'),
]

PDI_TEMPLATES = [
    ('Maîtriser {skill} pour progresser dans ma carrière', 'Obtenir une certification ou valider un projet concret'),
    ('Approfondir mes connaissances en {skill}', 'Score > 85 % aux évaluations de la formation'),
    ('Appliquer {skill} dans mon activité professionnelle', 'Livrable documenté soumis au formateur'),
    ('Passer du niveau débutant à intermédiaire en {skill}', 'Auto-évaluation confirmée par le formateur'),
]


def _slugify(name):
    replacements = {
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'â': 'a', 'à': 'a', 'ä': 'a',
        'î': 'i', 'ï': 'i',
        'ô': 'o', 'ö': 'o',
        'û': 'u', 'ü': 'u',
        'ç': 'c',
        '-': '', ' ': '',
    }
    result = name.lower()
    for src, dst in replacements.items():
        result = result.replace(src, dst)
    return result


class Command(BaseCommand):
    help = 'Create 20 B2C learners with rich learning data'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Remove existing B2C students before seeding')

    def handle(self, *args, **options):
        if options['reset']:
            self._reset()

        with transaction.atomic():
            learners = self._create_learners()
            skills   = self._seed_platform_skills()
            courses  = self._get_b2c_courses()
            self._seed_enrollments(learners, courses)
            self._seed_employee_skills(learners, skills)
            self._seed_pdi_plans(learners, skills, courses)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('  seed_b2c_learners completed!'))
        self.stdout.write(self.style.SUCCESS('=' * 50))

    # ─────────────────────────────────────────────────────────────────────────

    def _reset(self):
        from apps.accounts.models import User
        from apps.core.constants import Roles
        self.stdout.write('Removing existing B2C students...')
        emails = [
            f"{_slugify(first)}.{_slugify(last)}@exemple.com"
            for first, last, _ in LEARNER_NAMES
        ]
        count, _ = User.objects.filter(email__in=emails).delete()
        self.stdout.write(f'  Removed {count} records')

    def _create_learners(self):
        from apps.accounts.models import User
        from apps.core.constants import Roles
        learners = []
        created_count = 0
        for first, last, country_code in LEARNER_NAMES:
            email = f"{_slugify(first)}.{_slugify(last)}@exemple.com"
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first,
                    'last_name':  last,
                    'role':       Roles.STUDENT,
                    'company':    None,
                    'is_active':  True,
                    'country':    COUNTRY_LABELS.get(country_code, 'Afrique'),
                }
            )
            if created:
                user.set_password('learner123!')
                user.save(update_fields=['password'])
                created_count += 1
            learners.append(user)
        self.stdout.write(f'[+] Learners: {len(learners)} ({created_count} created)')
        return learners

    def _seed_platform_skills(self):
        from apps.hr_analytics.models import Skill
        skills = []
        for name, category in PLATFORM_SKILLS:
            skill, _ = Skill.objects.get_or_create(
                company=None, name=name,
                defaults={'category': category},
            )
            skills.append(skill)
        self.stdout.write(f'[+] Platform skills: {len(skills)}')
        return skills

    def _get_b2c_courses(self):
        from apps.courses.models import Course
        courses = list(Course.objects.filter(
            company__isnull=True, is_company_internal=False, status='published',
        ))
        self.stdout.write(f'[+] B2C courses available: {len(courses)}')
        return courses

    def _seed_enrollments(self, learners, courses):
        from apps.courses.models import Enrollment, Lesson
        from apps.progression.models import LessonProgress
        from apps.assessments.models import Assessment, AssessmentAttempt

        if not courses:
            self.stdout.write('[!] No B2C courses found — skipping enrollments')
            return

        en_created = lp_created = at_created = 0

        for learner in learners:
            # Each learner has a "profile" driving how much they completed
            profile = random.choices(['high', 'medium', 'low'], weights=[40, 40, 20])[0]
            n_courses = random.randint(3, min(8, len(courses)))
            chosen = random.sample(courses, n_courses)

            for course in chosen:
                enrollment, created = Enrollment.objects.get_or_create(
                    user=learner, course=course,
                    defaults={
                        'source': Enrollment.SOURCE_FREE,
                        'status': Enrollment.STATUS_IN_PROGRESS,
                    }
                )
                if created:
                    en_created += 1

                if profile == 'high':
                    completion_rate = random.uniform(0.75, 1.0)
                elif profile == 'medium':
                    completion_rate = random.uniform(0.35, 0.75)
                else:
                    completion_rate = random.uniform(0.05, 0.35)

                # LessonProgress
                lessons = list(Lesson.objects.filter(
                    chapter__section__course=course,
                ).order_by(
                    'chapter__section__order', 'chapter__order', 'order',
                ))
                n_complete = int(len(lessons) * completion_rate)

                for i, lesson in enumerate(lessons):
                    is_done = i < n_complete
                    watch_pct = Decimal(str(round(random.uniform(85, 100), 2))) if is_done \
                        else Decimal(str(round(random.uniform(0, 40), 2)))
                    lesson_dur = lesson.duration_seconds or 600  # default 10 min
                    lp, lp_new = LessonProgress.objects.get_or_create(
                        user=learner, lesson=lesson,
                        defaults={
                            'is_completed':  is_done,
                            'watch_percent': watch_pct,
                            'watched_seconds': int(float(watch_pct) / 100 * lesson_dur),
                            'completed_at':  _past(random.randint(1, 60)) if is_done else None,
                        }
                    )
                    if lp_new:
                        lp_created += 1

                # Mark enrollment completed if finished
                if completion_rate >= 0.95:
                    enrollment.status = Enrollment.STATUS_COMPLETED
                    enrollment.save(update_fields=['status'])

                # AssessmentAttempts
                if completion_rate >= 0.30:
                    assessments = list(Assessment.objects.filter(course=course, is_published=True))
                    for assessment in assessments:
                        score_val = (
                            random.uniform(65, 98) if profile == 'high'
                            else random.uniform(40, 80) if profile == 'medium'
                            else random.uniform(20, 60)
                        )
                        passing = float(assessment.passing_score or 70)
                        attempt, at_new = AssessmentAttempt.objects.get_or_create(
                            user=learner, assessment=assessment, attempt_number=1,
                            defaults={
                                'status':       AssessmentAttempt.STATUS_GRADED,
                                'score':        Decimal(str(round(score_val, 2))),
                                'is_passed':    score_val >= passing,
                                'submitted_at': _past(random.randint(1, 45)),
                            }
                        )
                        if at_new:
                            at_created += 1

        self.stdout.write(
            f'[+] Enrollments: {en_created} | LessonProgress: {lp_created} | Attempts: {at_created}'
        )

    def _seed_employee_skills(self, learners, skills):
        from apps.hr_analytics.models import EmployeeSkill
        created = 0
        for learner in learners:
            n = random.randint(4, 7)
            for skill in random.sample(skills, min(n, len(skills))):
                _, is_new = EmployeeSkill.objects.get_or_create(
                    user=learner, skill=skill,
                    defaults={'level': random.randint(1, 4), 'source': EmployeeSkill.SOURCE_AUTO},
                )
                if is_new:
                    created += 1
        self.stdout.write(f'[+] EmployeeSkills: {created} created')

    def _seed_pdi_plans(self, learners, skills, courses):
        from apps.hr_analytics.models import IndividualDevelopmentPlan, PDIObjective
        from apps.accounts.models import User
        from apps.core.constants import Roles

        creator = (
            User.objects.filter(role=Roles.TRAINING_CENTER_ADMIN).first()
            or User.objects.filter(role=Roles.SUPER_ADMIN).first()
            or learners[0]
        )

        n_with_plan = int(len(learners) * 0.65)
        created_plans = created_objs = 0

        for learner in random.sample(learners, min(n_with_plan, len(learners))):
            plan, created = IndividualDevelopmentPlan.objects.get_or_create(
                user=learner,
                period_start=_date_past(90),
                defaults={
                    'created_by': creator,
                    'period_end': _date_future(90),
                    'status': random.choices(
                        ['active', 'draft', 'completed'],
                        weights=[60, 20, 20],
                    )[0],
                }
            )
            if not created:
                continue
            created_plans += 1

            for skill in random.sample(skills, min(random.randint(2, 3), len(skills))):
                title_tpl, result_tpl = random.choice(PDI_TEMPLATES)
                PDIObjective.objects.create(
                    plan=plan,
                    skill=skill,
                    course=random.choice(courses) if courses and random.random() < 0.5 else None,
                    description=title_tpl.format(skill=skill.name),
                    target_date=_date_future(random.randint(30, 120)),
                    expected_result=result_tpl,
                    status=random.choices(
                        ['not_started', 'in_progress', 'achieved'],
                        weights=[30, 50, 20],
                    )[0],
                )
                created_objs += 1

        self.stdout.write(f'[+] PDI plans: {created_plans} | Objectives: {created_objs}')
