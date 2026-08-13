"""
Management command: seed_all
Populates the entire LMS system with realistic demo data.

Prerequisites: run `python manage.py seed_demo` first to create company + 7 users.

Usage:
    python manage.py seed_all
    python manage.py seed_all --reset   # wipe seeded data then re-create
"""

import random
import uuid
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

# Real YouTube video IDs for seed_all lessons
_SEED_ALL_YOUTUBE = {
    # Python pour la Data Science
    'Installation de Python & VS Code':               'rfscVS0vtbw',  # fCC Python Full Course
    'Jupyter Notebook en pratique':                   'kqtD5dpn9C8',  # Mosh Python
    'Votre premier programme Python':                 'x7X9w_GIm1s',  # Fireship Python 100s
    'Types primitifs en Python':                      'rfscVS0vtbw',
    'Listes et tuples':                               'rfscVS0vtbw',
    'Dictionnaires et ensembles':                     'rfscVS0vtbw',
    'Créer et charger un DataFrame':                  'dQw4w9WgXcQ',  # Pandas Tutorial (Keith Galli)
    'Filtrage et sélection de données':               'dQw4w9WgXcQ',
    # Management d'Équipe Agile
    'Manifeste Agile et ses valeurs':                 'sZoJ3gO4PSo',  # Scrum in 5 min
    'Scrum vs Kanban : comment choisir ?':            'sZoJ3gO4PSo',
    'Les rôles dans Scrum':                           'TRcReyRYIMg',  # Agile/Scrum course
    'Sprint Planning et backlog':                     'TRcReyRYIMg',
    'Daily Scrum et rétrospective':                   'TRcReyRYIMg',
    'Le modèle de Hersey & Blanchard':                'XU0llRltyFM',  # What great leaders do (TED)
    # Marketing Digital & Réseaux Sociaux
    'Panorama des leviers digitaux':                  'nU-IIXBWlS4',  # fCC Digital Marketing
    'Définir son buyer persona':                      'nU-IIXBWlS4',
    'Les 3 piliers du SEO':                           'dQw4w9WgXcQ',  # SEO Tutorial
    'Recherche de mots-clés':                         'dQw4w9WgXcQ',
    # Excel Avancé & Power BI
    'RECHERCHEV vs XLOOKUP':                          'dQw4w9WgXcQ',  # Excel XLOOKUP Tutorial
    'Formules matricielles':                          'dQw4w9WgXcQ',
    'Fonctions de base de données':                   'dQw4w9WgXcQ',
    'Créer un TCD depuis zéro':                       'g9qEhy7QKHA',  # Excel Pivot Tables
    'Champs calculés et groupement':                  'g9qEhy7QKHA',
    'Interface Power BI Desktop':                     'AGrl-H87pRU',  # Power BI Tutorial
    'Connexion aux sources de données':               'AGrl-H87pRU',
    'Votre premier rapport Power BI':                 'AGrl-H87pRU',
    # Communication Professionnelle
    'Structure d\'un e-mail efficace':                'dQw4w9WgXcQ',  # Business English Emails
    'Ton et formules de politesse':                   'dQw4w9WgXcQ',
    'La règle des 3 actes':                           'Nj-hdQMa3uA',  # TED Storytelling
    'Supports visuels percutants':                    'Nj-hdQMa3uA',
    'Gérer le trac':                                  'Ks-_Mh1QhMc',  # Amy Cuddy - Body Language TED
}


def _yt_all(title):
    vid = _SEED_ALL_YOUTUBE.get(title, 'dQw4w9WgXcQ')
    return f'https://www.youtube.com/embed/{vid}'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now():
    return timezone.now()


def _days(n):
    return _now() + timedelta(days=n)


def _date(n):
    return (date.today() + timedelta(days=n))


def _past(n):
    return _now() - timedelta(days=n)


def _past_date(n):
    return date.today() - timedelta(days=n)


# ---------------------------------------------------------------------------
# Seed data definitions
# ---------------------------------------------------------------------------

CATEGORIES = [
    {'name': 'Informatique & Technologie',       'icon': 'Monitor'},
    {'name': 'Management',                        'icon': 'Briefcase'},
    {'name': 'Leadership',                        'icon': 'Zap'},
    {'name': 'Ressources Humaines',               'icon': 'Users'},
    {'name': 'Marketing Digital',                 'icon': 'TrendingUp'},
    {'name': 'Finance & Comptabilité',            'icon': 'DollarSign'},
    {'name': 'Communication',                     'icon': 'MessageSquare'},
    {'name': 'IA & Intelligence Artificielle',    'icon': 'Brain'},
    {'name': 'Cybersécurité',                     'icon': 'Shield'},
    {'name': 'Santé & Bien-être',                 'icon': 'Heart'},
    {'name': 'Industrie & Production',            'icon': 'Factory'},
    {'name': 'Agriculture & Agroalimentaire',     'icon': 'Leaf'},
    {'name': 'Langues Étrangères',                'icon': 'Globe'},
    {'name': 'Soft Skills',                       'icon': 'Smile'},
    {'name': 'Droit & Conformité',                'icon': 'Scale'},
    {'name': 'Développement Personnel',           'icon': 'Star'},
]

COURSES_DATA = [
    {
        'title': 'Python pour la Data Science',
        'subtitle': 'Maîtrisez Python, Pandas et les visualisations de données',
        'description': (
            'Ce cours vous guide de débutant à pratiquant en Python appliqué '
            'à la data science. Vous apprendrez à manipuler des données avec Pandas, '
            'créer des visualisations avec Matplotlib et construire vos premiers modèles.'
        ),
        'level': 'beginner',
        'category': 'Informatique & Technologie',
        'price': 49000,
        'requirements': ['Aucun prérequis', 'Un ordinateur avec connexion internet'],
        'what_you_will_learn': [
            'Maîtriser les bases de Python',
            'Manipuler des données avec Pandas',
            'Créer des visualisations avec Matplotlib',
            'Appliquer les algorithmes ML de base',
        ],
        'sections': [
            {
                'title': 'Introduction à Python',
                'chapters': [
                    {
                        'title': 'Environnement de travail',
                        'lessons': [
                            {'title': 'Installation de Python & VS Code', 'content_type': 'video', 'duration_seconds': 900, 'is_preview_free': True},
                            {'title': 'Jupyter Notebook en pratique', 'content_type': 'video', 'duration_seconds': 720},
                            {'title': 'Votre premier programme Python', 'content_type': 'text', 'duration_seconds': 600},
                        ],
                    },
                    {
                        'title': 'Variables et types de données',
                        'lessons': [
                            {'title': 'Types primitifs en Python', 'content_type': 'video', 'duration_seconds': 840},
                            {'title': 'Listes et tuples', 'content_type': 'video', 'duration_seconds': 780},
                            {'title': 'Dictionnaires et ensembles', 'content_type': 'video', 'duration_seconds': 660},
                        ],
                    },
                ],
            },
            {
                'title': 'Pandas & Manipulation de données',
                'chapters': [
                    {
                        'title': 'DataFrames et Series',
                        'lessons': [
                            {'title': 'Créer et charger un DataFrame', 'content_type': 'video', 'duration_seconds': 1020},
                            {'title': 'Filtrage et sélection de données', 'content_type': 'video', 'duration_seconds': 900},
                            {'title': 'Exercice pratique — Nettoyage de données', 'content_type': 'text', 'duration_seconds': 1800},
                        ],
                    },
                ],
            },
        ],
        'quiz': {
            'title': 'Quiz — Python Fondamentaux',
            'questions': [
                {
                    'text': 'Quelle méthode Pandas permet d\'afficher les premières lignes d\'un DataFrame ?',
                    'choices': [
                        {'text': 'df.head()', 'is_correct': True},
                        {'text': 'df.first()', 'is_correct': False},
                        {'text': 'df.show()', 'is_correct': False},
                        {'text': 'df.top()', 'is_correct': False},
                    ],
                    'explanation': 'La méthode head() retourne par défaut les 5 premières lignes.',
                },
                {
                    'text': 'Quel est le type de données correspondant à une valeur décimale en Python ?',
                    'choices': [
                        {'text': 'float', 'is_correct': True},
                        {'text': 'int', 'is_correct': False},
                        {'text': 'str', 'is_correct': False},
                        {'text': 'decimal', 'is_correct': False},
                    ],
                    'explanation': 'Le type float représente les nombres à virgule flottante.',
                },
                {
                    'text': 'Comment créer une liste vide en Python ?',
                    'choices': [
                        {'text': '[]', 'is_correct': True},
                        {'text': 'list.new()', 'is_correct': False},
                        {'text': 'new List()', 'is_correct': False},
                        {'text': '{}', 'is_correct': False},
                    ],
                    'explanation': '[] est la syntaxe littérale d\'une liste vide.',
                },
            ],
        },
    },
    {
        'title': 'Management d\'Équipe Agile',
        'subtitle': 'Scrum, Kanban et leadership situationnel',
        'description': (
            'Devenez un manager agile efficace. Ce cours couvre Scrum, Kanban, '
            'le leadership situationnel et les techniques de motivation d\'équipe '
            'dans un contexte de travail hybride.'
        ),
        'level': 'intermediate',
        'category': 'Management & Leadership',
        'price': 65000,
        'requirements': ['Expérience de management requise', 'Connaissance des fondamentaux du management'],
        'what_you_will_learn': [
            'Appliquer la méthode Scrum',
            'Visualiser le flux de travail avec Kanban',
            'Adapter son leadership à la maturité de l\'équipe',
            'Conduire des réunions efficaces',
        ],
        'sections': [
            {
                'title': 'Les Méthodes Agiles',
                'chapters': [
                    {
                        'title': 'Introduction à l\'Agilité',
                        'lessons': [
                            {'title': 'Manifeste Agile et ses valeurs', 'content_type': 'video', 'duration_seconds': 1080, 'is_preview_free': True},
                            {'title': 'Scrum vs Kanban : comment choisir ?', 'content_type': 'video', 'duration_seconds': 960},
                        ],
                    },
                    {
                        'title': 'Scrum en pratique',
                        'lessons': [
                            {'title': 'Les rôles dans Scrum', 'content_type': 'video', 'duration_seconds': 840},
                            {'title': 'Sprint Planning et backlog', 'content_type': 'video', 'duration_seconds': 1140},
                            {'title': 'Daily Scrum et rétrospective', 'content_type': 'video', 'duration_seconds': 720},
                        ],
                    },
                ],
            },
            {
                'title': 'Leadership Situationnel',
                'chapters': [
                    {
                        'title': 'Styles de leadership',
                        'lessons': [
                            {'title': 'Le modèle de Hersey & Blanchard', 'content_type': 'video', 'duration_seconds': 1200},
                            {'title': 'Cas pratiques de leadership', 'content_type': 'text', 'duration_seconds': 1800},
                        ],
                    },
                ],
            },
        ],
        'quiz': {
            'title': 'Quiz — Management Agile',
            'questions': [
                {
                    'text': 'Quelle est la durée recommandée d\'un sprint Scrum ?',
                    'choices': [
                        {'text': '1 à 4 semaines', 'is_correct': True},
                        {'text': '1 à 3 mois', 'is_correct': False},
                        {'text': '1 semaine exactement', 'is_correct': False},
                        {'text': '6 mois', 'is_correct': False},
                    ],
                    'explanation': 'Le sprint dure en général 1 à 4 semaines selon le guide Scrum officiel.',
                },
                {
                    'text': 'Dans le leadership situationnel, quel style convient à un collaborateur très motivé mais peu compétent ?',
                    'choices': [
                        {'text': 'Directif (S1)', 'is_correct': True},
                        {'text': 'Délégation (S4)', 'is_correct': False},
                        {'text': 'Coaching (S2)', 'is_correct': False},
                        {'text': 'Soutien (S3)', 'is_correct': False},
                    ],
                    'explanation': 'Le style S1 (Telling/Directif) est adapté aux débutants motivés.',
                },
            ],
        },
    },
    {
        'title': 'Marketing Digital & Réseaux Sociaux',
        'subtitle': 'Stratégie de contenu, SEO, Google Ads et analytics',
        'description': (
            'Maîtrisez le marketing digital de A à Z : stratégie de contenu, '
            'référencement naturel, publicité payante, e-mail marketing et mesure de performance.'
        ),
        'level': 'all_levels',
        'category': 'Marketing Digital',
        'price': 39000,
        'is_free': False,
        'requirements': ['Connexion internet', 'Compte Google (gratuit)'],
        'what_you_will_learn': [
            'Définir une stratégie digitale',
            'Optimiser un site pour le SEO',
            'Créer des campagnes Google Ads',
            'Analyser les performances avec GA4',
        ],
        'sections': [
            {
                'title': 'Fondamentaux du Marketing Digital',
                'chapters': [
                    {
                        'title': 'L\'écosystème digital',
                        'lessons': [
                            {'title': 'Panorama des leviers digitaux', 'content_type': 'video', 'duration_seconds': 900, 'is_preview_free': True},
                            {'title': 'Définir son buyer persona', 'content_type': 'video', 'duration_seconds': 840},
                        ],
                    },
                ],
            },
            {
                'title': 'SEO & Contenu',
                'chapters': [
                    {
                        'title': 'Référencement naturel',
                        'lessons': [
                            {'title': 'Les 3 piliers du SEO', 'content_type': 'video', 'duration_seconds': 1080},
                            {'title': 'Recherche de mots-clés', 'content_type': 'video', 'duration_seconds': 960},
                            {'title': 'Optimisation on-page', 'content_type': 'text', 'duration_seconds': 1200},
                        ],
                    },
                ],
            },
        ],
        'quiz': {
            'title': 'Quiz — Marketing Digital',
            'questions': [
                {
                    'text': 'Qu\'est-ce que le taux de rebond (bounce rate) ?',
                    'choices': [
                        {'text': 'Le % de visiteurs quittant le site après une seule page', 'is_correct': True},
                        {'text': 'Le % de clics sur une publicité', 'is_correct': False},
                        {'text': 'Le nombre d\'e-mails non ouverts', 'is_correct': False},
                        {'text': 'Le % de pages indexées par Google', 'is_correct': False},
                    ],
                    'explanation': 'Le bounce rate mesure les sessions d\'une seule page sans interaction.',
                },
                {
                    'text': 'Quel outil Google est principalement utilisé pour l\'analyse du trafic web ?',
                    'choices': [
                        {'text': 'Google Analytics', 'is_correct': True},
                        {'text': 'Google Search Console', 'is_correct': False},
                        {'text': 'Google Ads', 'is_correct': False},
                        {'text': 'Google Tag Manager', 'is_correct': False},
                    ],
                    'explanation': 'Google Analytics (GA4) est l\'outil d\'analyse de trafic de référence.',
                },
            ],
        },
    },
    {
        'title': 'Excel Avancé & Power BI',
        'subtitle': 'Tableaux croisés dynamiques, macros VBA et dashboards interactifs',
        'description': (
            'Passez à la vitesse supérieure avec Excel et Power BI. '
            'Formules avancées, tableaux croisés dynamiques, macros VBA et '
            'création de tableaux de bord interactifs pour piloter votre activité.'
        ),
        'level': 'intermediate',
        'category': 'Finance & Comptabilité',
        'price': 29000,
        'requirements': ['Connaissance de base d\'Excel'],
        'what_you_will_learn': [
            'Maîtriser les formules avancées (INDEX/MATCH, XLOOKUP)',
            'Créer des tableaux croisés dynamiques',
            'Automatiser avec les macros VBA',
            'Construire des dashboards Power BI',
        ],
        'sections': [
            {
                'title': 'Excel Avancé',
                'chapters': [
                    {
                        'title': 'Formules Puissantes',
                        'lessons': [
                            {'title': 'RECHERCHEV vs XLOOKUP', 'content_type': 'video', 'duration_seconds': 960, 'is_preview_free': True},
                            {'title': 'Formules matricielles', 'content_type': 'video', 'duration_seconds': 840},
                            {'title': 'Fonctions de base de données', 'content_type': 'video', 'duration_seconds': 720},
                        ],
                    },
                    {
                        'title': 'Tableaux Croisés Dynamiques',
                        'lessons': [
                            {'title': 'Créer un TCD depuis zéro', 'content_type': 'video', 'duration_seconds': 1080},
                            {'title': 'Champs calculés et groupement', 'content_type': 'video', 'duration_seconds': 900},
                        ],
                    },
                ],
            },
            {
                'title': 'Power BI',
                'chapters': [
                    {
                        'title': 'Introduction à Power BI',
                        'lessons': [
                            {'title': 'Interface Power BI Desktop', 'content_type': 'video', 'duration_seconds': 780},
                            {'title': 'Connexion aux sources de données', 'content_type': 'video', 'duration_seconds': 900},
                            {'title': 'Votre premier rapport Power BI', 'content_type': 'video', 'duration_seconds': 1200},
                        ],
                    },
                ],
            },
        ],
        'quiz': {
            'title': 'Quiz — Excel & Power BI',
            'questions': [
                {
                    'text': 'Quelle fonction Excel renvoie la position d\'une valeur dans une plage ?',
                    'choices': [
                        {'text': 'MATCH()', 'is_correct': True},
                        {'text': 'INDEX()', 'is_correct': False},
                        {'text': 'VLOOKUP()', 'is_correct': False},
                        {'text': 'FIND()', 'is_correct': False},
                    ],
                    'explanation': 'MATCH() retourne la position relative d\'une valeur dans une plage.',
                },
            ],
        },
    },
    {
        'title': 'Communication Professionnelle',
        'subtitle': 'Prise de parole, e-mails, présentations et gestion des conflits',
        'description': (
            'Améliorez vos compétences en communication professionnelle : '
            'rédaction d\'e-mails percutants, présentation orale convaincante, '
            'écoute active et gestion constructive des conflits.'
        ),
        'level': 'all_levels',
        'category': 'Communication',
        'price': 0,
        'is_free': True,
        'requirements': [],
        'what_you_will_learn': [
            'Rédiger des e-mails clairs et percutants',
            'Préparer et animer une présentation',
            'Pratiquer l\'écoute active',
            'Gérer les conflits de façon constructive',
        ],
        'sections': [
            {
                'title': 'Communication Écrite',
                'chapters': [
                    {
                        'title': 'E-mails Professionnels',
                        'lessons': [
                            {'title': 'Structure d\'un e-mail efficace', 'content_type': 'video', 'duration_seconds': 720, 'is_preview_free': True},
                            {'title': 'Ton et formules de politesse', 'content_type': 'text', 'duration_seconds': 600},
                        ],
                    },
                ],
            },
            {
                'title': 'Prise de Parole en Public',
                'chapters': [
                    {
                        'title': 'Préparer sa présentation',
                        'lessons': [
                            {'title': 'La règle des 3 actes', 'content_type': 'video', 'duration_seconds': 900},
                            {'title': 'Supports visuels percutants', 'content_type': 'video', 'duration_seconds': 840},
                            {'title': 'Gérer le trac', 'content_type': 'video', 'duration_seconds': 660},
                        ],
                    },
                ],
            },
        ],
        'quiz': {
            'title': 'Quiz — Communication Pro',
            'questions': [
                {
                    'text': 'Quelle est la première chose à préciser dans un e-mail professionnel ?',
                    'choices': [
                        {'text': 'L\'objet clair et concis', 'is_correct': True},
                        {'text': 'La signature électronique', 'is_correct': False},
                        {'text': 'Les pièces jointes', 'is_correct': False},
                        {'text': 'Les destinataires en copie', 'is_correct': False},
                    ],
                    'explanation': 'Un objet précis augmente le taux d\'ouverture et la compréhension.',
                },
            ],
        },
    },
]

SKILLS_DATA = [
    # Technique
    {'name': 'Python', 'category': 'Technique'},
    {'name': 'Data Science', 'category': 'Technique'},
    {'name': 'Excel Avancé', 'category': 'Technique'},
    {'name': 'Power BI', 'category': 'Technique'},
    {'name': 'SQL', 'category': 'Technique'},
    # Management
    {'name': 'Scrum / Agile', 'category': 'Management'},
    {'name': 'Leadership', 'category': 'Management'},
    {'name': 'Gestion de projet', 'category': 'Management'},
    # Communication
    {'name': 'Communication orale', 'category': 'Communication'},
    {'name': 'Rédaction professionnelle', 'category': 'Communication'},
    {'name': 'Prise de parole en public', 'category': 'Communication'},
    # Marketing
    {'name': 'SEO', 'category': 'Marketing'},
    {'name': 'Google Ads', 'category': 'Marketing'},
    {'name': 'Marketing de contenu', 'category': 'Marketing'},
]

JOB_ROLES_DATA = [
    'Chef de Projet Digital',
    'Data Analyst',
    'Responsable Marketing',
    'Chargé de Communication',
    'Contrôleur de Gestion',
    'Business Developer',
]


class Command(BaseCommand):
    help = 'Seed the entire LMS system with realistic demo data'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Wipe seeded data then re-create')

    def log(self, msg):
        self.stdout.write(msg)

    def ok(self, msg):
        self.stdout.write(self.style.SUCCESS(f'  [+] {msg}'))

    def skip(self, msg):
        self.stdout.write(f'  [=] {msg}')

    def warn(self, msg):
        self.stdout.write(self.style.WARNING(f'  [!] {msg}'))

    def handle(self, *args, **options):
        from apps.accounts.models import User
        from apps.tenants.models import Company, Department, Service, Team
        from apps.catalog.models import Category
        from apps.courses.models import (
            Course, CourseSection, Chapter, Lesson, Enrollment, Review,
        )
        from apps.assessments.models import (
            QuestionBank, Question, QuestionChoice,
            Assessment, AssessmentQuestion, AssessmentAttempt,
        )
        from apps.gamification.models import (
            Level, Badge, UserBadge, XPLog, Challenge, ChallengeParticipation,
        )
        from apps.learning_paths.models import (
            LearningPath, LearningPathStep, LearningPathEnrollment,
            TrainingSession, SessionParticipant,
        )
        from apps.virtual_classes.models import VirtualClass
        from apps.hr_analytics.models import (
            Skill, CourseSkill, JobRole, JobRoleSkillRequirement,
            EmployeeSkill, IndividualDevelopmentPlan, PDIObjective,
            Evaluation360Campaign, Evaluation360Response, TrainingBudgetEntry,
        )
        from apps.social.models import (
            ForumThread, ForumPost, LearningGroup,
            MentorshipRelation, Conversation, Message,
        )
        from apps.notifications.models import Notification, NotificationPreference
        from apps.certificates.models import CertificateTemplate, Certificate

        reset = options['reset']
        if reset:
            self._reset(Course, Assessment, LearningPath, TrainingSession, VirtualClass)

        try:
            company = Company.objects.get(slug='lmspro-demo')
        except Company.DoesNotExist:
            self.warn('Company "lmspro-demo" not found — run seed_demo first!')
            return

        # Fetch all 7 demo users
        users = {u.role: u for u in User.objects.filter(
            email__in=[
                'superadmin@lmspro.com', 'admin@lmspro.com', 'hr@lmspro.com',
                'manager@lmspro.com', 'trainer@lmspro.com', 'employee@lmspro.com',
                'student@lmspro.com',
            ]
        )}
        if not users:
            self.warn('Demo users not found — run seed_demo first!')
            return

        trainer = users.get('trainer')
        employee = users.get('employee')
        student = users.get('student')
        manager = users.get('manager')
        hr_user = users.get('hr')
        admin_user = users.get('company_admin')

        with transaction.atomic():
            # ── 1. Departments / Services / Teams ────────────────────────────
            self.log('\n[1] Organisation...')
            dept_it, _ = Department.objects.get_or_create(
                company=company, name='Direction Informatique', defaults={'code': 'DIT'},
            )
            dept_mkt, _ = Department.objects.get_or_create(
                company=company, name='Marketing & Communication', defaults={'code': 'MKT'},
            )
            dept_fin, _ = Department.objects.get_or_create(
                company=company, name='Finance & Contrôle de Gestion', defaults={'code': 'FIN'},
            )
            dept_dg, _ = Department.objects.get_or_create(
                company=company, name='Direction Générale', defaults={'code': 'DG'},
            )
            svc_dev, _ = Service.objects.get_or_create(
                department=dept_it, name='Développement Logiciel',
                defaults={'company': company},
            )
            team_data, _ = Team.objects.get_or_create(
                company=company, name='Équipe Data',
                defaults={'manager': manager, 'service': svc_dev},
            )
            self.ok('Departments / Services / Teams OK')

            # Assign users to departments
            for u in [manager, employee]:
                if u and not u.department_id:
                    u.department = dept_dg
                    u.save(update_fields=['department'])
            if trainer and not trainer.department_id:
                trainer.department = dept_it
                trainer.save(update_fields=['department'])
            if hr_user and not hr_user.department_id:
                hr_user.department = dept_dg
                hr_user.save(update_fields=['department'])

            # ── 2. Categories ─────────────────────────────────────────────────
            self.log('\n[2] Categories...')
            cat_objects = {}
            for c in CATEGORIES:
                obj, created = Category.objects.get_or_create(
                    name=c['name'],
                    defaults={'icon': c['icon'], 'is_active': True},
                )
                cat_objects[c['name']] = obj
                if created:
                    self.ok(f'Category: {obj.name}')
                else:
                    self.skip(f'Category: {obj.name}')

            # ── 3. Courses ─────────────────────────────────────────────────────
            self.log('\n[3] Courses...')
            course_objects = []
            bank_map = {}  # course title → question bank

            for cd in COURSES_DATA:
                cat = cat_objects.get(cd['category'])
                course, created = Course.objects.get_or_create(
                    title=cd['title'],
                    defaults={
                        'company': company,
                        'category': cat,
                        'instructor': trainer,
                        'subtitle': cd.get('subtitle', ''),
                        'description': cd.get('description', ''),
                        'level': cd.get('level', 'all_levels'),
                        'price': cd.get('price', 0),
                        'is_free': cd.get('is_free', cd.get('price', 1) == 0),
                        'status': 'published',
                        'requirements': cd.get('requirements', []),
                        'what_you_will_learn': cd.get('what_you_will_learn', []),
                        'certificate_enabled': True,
                        'published_at': _past(30),
                        'is_company_internal': True,
                    },
                )
                if created:
                    self.ok(f'Course: {course.title}')
                else:
                    self.skip(f'Course: {course.title}')
                course_objects.append(course)

                # Sections → Chapters → Lessons
                first_lesson = None
                for s_idx, section_data in enumerate(cd.get('sections', [])):
                    section, _ = CourseSection.objects.get_or_create(
                        course=course, title=section_data['title'],
                        defaults={'order': s_idx},
                    )
                    for c_idx, chapter_data in enumerate(section_data.get('chapters', [])):
                        chapter, _ = Chapter.objects.get_or_create(
                            section=section, title=chapter_data['title'],
                            defaults={'order': c_idx},
                        )
                        for l_idx, lesson_data in enumerate(chapter_data.get('lessons', [])):
                            lesson, created = Lesson.objects.get_or_create(
                                chapter=chapter, title=lesson_data['title'],
                                defaults={
                                    'order': l_idx,
                                    'content_type': lesson_data.get('content_type', 'video'),
                                    'duration_seconds': lesson_data.get('duration_seconds', 600),
                                    'is_preview_free': lesson_data.get('is_preview_free', False),
                                    'text_content': (
                                        f'Contenu de la leçon : {lesson_data["title"]}.\n\n'
                                        'Ce contenu pédagogique couvre les concepts essentiels '
                                        'abordés dans cette leçon.'
                                    ) if lesson_data.get('content_type') == 'text' else '',
                                    'external_embed_url': (
                                        _yt_all(lesson_data['title'])
                                    ) if lesson_data.get('content_type') == 'video' else '',
                                },
                            )
                            if not created and lesson_data.get('content_type') == 'video':
                                lesson.external_embed_url = _yt_all(lesson_data['title'])
                                lesson.save(update_fields=['external_embed_url'])
                            if first_lesson is None:
                                first_lesson = lesson

                # Question Bank + Quiz
                quiz_data = cd.get('quiz')
                if quiz_data:
                    bank, _ = QuestionBank.objects.get_or_create(
                        title=quiz_data['title'],
                        defaults={'company': company, 'created_by': trainer},
                    )
                    bank_map[cd['title']] = bank

                    for q_idx, qd in enumerate(quiz_data.get('questions', [])):
                        question, _ = Question.objects.get_or_create(
                            bank=bank, text=qd['text'],
                            defaults={
                                'question_type': 'mcq',
                                'points': 1,
                                'explanation': qd.get('explanation', ''),
                                'difficulty': 'medium',
                            },
                        )
                        for ch_idx, choice in enumerate(qd.get('choices', [])):
                            QuestionChoice.objects.get_or_create(
                                question=question, text=choice['text'],
                                defaults={'is_correct': choice['is_correct'], 'order': ch_idx},
                            )

                    # Assessment
                    assessment, _ = Assessment.objects.get_or_create(
                        course=course, title=quiz_data['title'],
                        defaults={
                            'assessment_type': 'quiz',
                            'instructions': 'Répondez à chaque question avec soin.',
                            'time_limit_minutes': 30,
                            'max_attempts': 3,
                            'passing_score': 70,
                            'is_randomized': False,
                            'question_bank': bank,
                            'is_published': True,
                        },
                    )
                    # Link questions
                    questions_in_bank = list(bank.questions.all())
                    for q_idx, q in enumerate(questions_in_bank):
                        AssessmentQuestion.objects.get_or_create(
                            assessment=assessment, question=q,
                            defaults={'order': q_idx},
                        )

            # ── 4. Enrollments ─────────────────────────────────────────────────
            self.log('\n[4] Enrollments...')
            learners = [u for u in [employee, student, manager] if u]
            for learner in learners:
                for i, course in enumerate(course_objects):
                    progress = random.choice([25, 50, 75, 100]) if i < 3 else random.choice([10, 30])
                    status = 'completed' if progress == 100 else 'in_progress'
                    enrollment, created = Enrollment.objects.get_or_create(
                        user=learner, course=course,
                        defaults={
                            'source': 'assigned',
                            'status': status,
                            'progress_percent': progress,
                            'assigned_by': manager,
                            'completed_at': _past(5) if status == 'completed' else None,
                        },
                    )
                    if created:
                        self.ok(f'Enrollment: {learner.email} -> {course.title}')

            # ── 5. Reviews ─────────────────────────────────────────────────────
            self.log('\n[5] Reviews...')
            review_comments = [
                'Excellent cours, très bien structuré !',
                'Formateur très pédagogue, je recommande.',
                'Contenu de qualité, exemples concrets.',
                'Formation complète et claire. Merci !',
                'Très utile pour ma pratique quotidienne.',
            ]
            for learner in [employee, student]:
                if not learner:
                    continue
                for course in course_objects[:3]:
                    Review.objects.get_or_create(
                        user=learner, course=course,
                        defaults={
                            'rating': random.randint(4, 5),
                            'comment': random.choice(review_comments),
                        },
                    )
            self.ok('Reviews created')

            # ── 6. Assessment Attempts ─────────────────────────────────────────
            self.log('\n[6] Assessment Attempts...')
            for learner in learners:
                for course in course_objects[:3]:
                    assessment_qs = Assessment.objects.filter(course=course)
                    for assessment in assessment_qs:
                        score = random.choice([65, 75, 85, 90, 95])
                        attempt, created = AssessmentAttempt.objects.get_or_create(
                            assessment=assessment, user=learner, attempt_number=1,
                            defaults={
                                'submitted_at': _past(random.randint(3, 20)),
                                'score': score,
                                'is_passed': score >= 70,
                                'status': 'graded',
                            },
                        )
                        if created:
                            self.ok(f'Attempt: {learner.email} – {assessment.title} ({score}%)')

            # ── 7. Certificates ─────────────────────────────────────────────────
            self.log('\n[7] Certificates...')
            template, _ = CertificateTemplate.objects.get_or_create(
                name='Modèle Standard LMS PRO',
                defaults={'company': company, 'is_default': True, 'layout_config': {'logo': True}},
            )
            for learner in [employee, student]:
                if not learner:
                    continue
                for course in course_objects[:2]:
                    cert_num = f'LMSPRO-{learner.id:04d}-{course.id:04d}-{uuid.uuid4().hex[:6].upper()}'
                    Certificate.objects.get_or_create(
                        user=learner, course=course,
                        defaults={
                            'template': template,
                            'certificate_number': cert_num,
                            'verification_code': uuid.uuid4().hex,
                        },
                    )
            self.ok('Certificates created')

            # ── 8. Gamification ─────────────────────────────────────────────────
            self.log('\n[8] Gamification...')

            # Levels
            levels_data = [
                {'name': 'Débutant',       'min_xp': 0,    'icon': 'Seedling'},
                {'name': 'Apprenti',       'min_xp': 100,  'icon': 'BookOpen'},
                {'name': 'Praticien',      'min_xp': 300,  'icon': 'Zap'},
                {'name': 'Expert',         'min_xp': 700,  'icon': 'Star'},
                {'name': 'Maître',         'min_xp': 1500, 'icon': 'Trophy'},
                {'name': 'Grand Maître',   'min_xp': 3000, 'icon': 'Crown'},
            ]
            for ld in levels_data:
                Level.objects.get_or_create(name=ld['name'], defaults={'min_xp': ld['min_xp'], 'icon': ld['icon']})
            self.ok('Levels created')

            # Badges
            badges_data = [
                {'title': 'Premier Pas',   'criteria_type': 'course_completion', 'criteria_value': {'min_completions': 1}},
                {'title': 'Assidu',        'criteria_type': 'streak',            'criteria_value': {'days': 7}},
                {'title': 'Centurion',     'criteria_type': 'xp_threshold',      'criteria_value': {'xp': 100}},
                {'title': 'Expert Métier', 'criteria_type': 'skill_mastery',     'criteria_value': {'level': 4}},
                {'title': 'Polyglotte',    'criteria_type': 'course_completion', 'criteria_value': {'min_completions': 5}},
                {'title': 'Champion',      'criteria_type': 'xp_threshold',      'criteria_value': {'xp': 1000}},
            ]
            badge_objects = []
            for bd in badges_data:
                badge, _ = Badge.objects.get_or_create(
                    title=bd['title'],
                    defaults={
                        'company': company,
                        'description': f'Récompense pour : {bd["title"]}',
                        'criteria_type': bd['criteria_type'],
                        'criteria_value': bd['criteria_value'],
                    },
                )
                badge_objects.append(badge)
            self.ok('Badges created')

            # XP Logs & UserBadges
            xp_reasons = [
                ('Connexion quotidienne', 10, 'login'),
                ('Leçon complétée', 25, 'lesson_completion'),
                ('Quiz réussi', 50, 'quiz_passed'),
                ('Cours terminé', 150, 'course_completion'),
                ('Commentaire de forum', 15, 'forum_post'),
            ]
            for learner in learners:
                for reason, amount, source in xp_reasons:
                    XPLog.objects.get_or_create(
                        user=learner, reason=reason, source_type=source,
                        defaults={'amount': amount},
                    )
                # Award first 2 badges
                for badge in badge_objects[:2]:
                    UserBadge.objects.get_or_create(user=learner, badge=badge)
            self.ok('XP Logs & UserBadges created')

            # Challenges
            challenge1, _ = Challenge.objects.get_or_create(
                title='Défi Juin — 3 cours ce mois',
                defaults={
                    'company': company,
                    'description': 'Terminez 3 cours avant la fin du mois pour gagner 500 XP.',
                    'start_date': _past_date(15),
                    'end_date': _date(15),
                    'xp_reward': 500,
                    'badge_reward': badge_objects[4] if len(badge_objects) > 4 else None,
                    'criteria': {'type': 'course_completion', 'count': 3},
                },
            )
            challenge2, _ = Challenge.objects.get_or_create(
                title='Défi Quiz — Score parfait',
                defaults={
                    'company': company,
                    'description': 'Obtenez 100% à n\'importe quel quiz pour gagner 200 XP.',
                    'start_date': _past_date(5),
                    'end_date': _date(25),
                    'xp_reward': 200,
                    'criteria': {'type': 'quiz_score', 'score': 100},
                },
            )
            for learner in learners:
                ChallengeParticipation.objects.get_or_create(
                    challenge=challenge1, user=learner,
                    defaults={'status': 'joined'},
                )
                ChallengeParticipation.objects.get_or_create(
                    challenge=challenge2, user=learner,
                    defaults={'status': 'joined'},
                )
            self.ok('Challenges created')

            # ── 9. Learning Paths ──────────────────────────────────────────────
            self.log('\n[9] Learning Paths...')
            path1, _ = LearningPath.objects.get_or_create(
                title='Parcours Data Analyst',
                defaults={
                    'company': company,
                    'description': 'Devenez Data Analyst en maîtrisant Python, Excel avancé et Power BI.',
                    'path_type': 'job_role',
                    'target_job_title': 'Data Analyst',
                    'created_by': hr_user,
                    'is_active': True,
                    'certificate_enabled': True,
                },
            )
            path2, _ = LearningPath.objects.get_or_create(
                title='Parcours Manager Digital',
                defaults={
                    'company': company,
                    'description': 'Développez vos compétences managériales et digitales.',
                    'path_type': 'manager',
                    'created_by': hr_user,
                    'is_active': True,
                    'certificate_enabled': True,
                },
            )
            path3, _ = LearningPath.objects.get_or_create(
                title='Onboarding Nouveaux Collaborateurs',
                defaults={
                    'company': company,
                    'description': 'Parcours de prise en main pour les nouveaux arrivants.',
                    'path_type': 'onboarding',
                    'created_by': hr_user,
                    'is_active': True,
                },
            )

            # Link courses to paths
            path1_courses = course_objects[:2]  # Python + Management
            path2_courses = course_objects[1:4]  # Management + Marketing + Excel
            path3_courses = course_objects[4:]   # Communication

            for path, courses in [(path1, path1_courses), (path2, path2_courses), (path3, path3_courses)]:
                for idx, course in enumerate(courses):
                    LearningPathStep.objects.get_or_create(
                        path=path, course=course,
                        defaults={'order': idx, 'is_mandatory': idx == 0},
                    )

            # Path Enrollments
            for learner in learners:
                LearningPathEnrollment.objects.get_or_create(
                    user=learner, path=path1,
                    defaults={
                        'status': 'in_progress',
                        'progress_percent': random.choice([20, 40, 60]),
                        'started_at': _past(10),
                        'assigned_by': hr_user,
                    },
                )
                LearningPathEnrollment.objects.get_or_create(
                    user=learner, path=path3,
                    defaults={
                        'status': 'not_started',
                        'progress_percent': 0,
                        'assigned_by': hr_user,
                    },
                )
            self.ok('Learning Paths created')

            # ── 10. Training Sessions ──────────────────────────────────────────
            self.log('\n[10] Training Sessions...')
            sessions_data = [
                {
                    'title': 'Session Python — Groupe A',
                    'course': course_objects[0],
                    'location_type': 'online',
                    'join_url': 'https://meet.jit.si/lmspro-python-groupe-a',
                    'start_datetime': _days(7).replace(hour=9, minute=0, second=0, microsecond=0),
                    'end_datetime': _days(7).replace(hour=12, minute=0, second=0, microsecond=0),
                    'capacity': 20,
                },
                {
                    'title': 'Atelier Management Agile',
                    'course': course_objects[1],
                    'location_type': 'onsite',
                    'address': 'Dakar, Immeuble SODIDA, Salle de formation',
                    'start_datetime': _days(14).replace(hour=8, minute=30, second=0, microsecond=0),
                    'end_datetime': _days(14).replace(hour=17, minute=0, second=0, microsecond=0),
                    'capacity': 15,
                },
                {
                    'title': 'Webinaire Marketing Digital',
                    'course': course_objects[2],
                    'location_type': 'online',
                    'join_url': 'https://zoom.us/j/9876543210',
                    'start_datetime': _days(3).replace(hour=14, minute=0, second=0, microsecond=0),
                    'end_datetime': _days(3).replace(hour=16, minute=0, second=0, microsecond=0),
                    'capacity': 50,
                },
                {
                    'title': 'Formation Excel & Power BI — Juin',
                    'course': course_objects[3],
                    'location_type': 'onsite',
                    'address': 'Abidjan, Plateau, Centre de formation',
                    'start_datetime': _past(5).replace(hour=9, minute=0, second=0, microsecond=0),
                    'end_datetime': _past(5).replace(hour=17, minute=0, second=0, microsecond=0),
                    'capacity': 12,
                },
            ]
            session_objects = []
            for sd in sessions_data:
                session, created = TrainingSession.objects.get_or_create(
                    title=sd['title'],
                    defaults={
                        'company': company,
                        'course': sd['course'],
                        'trainer': trainer,
                        'location_type': sd['location_type'],
                        'address': sd.get('address', ''),
                        'join_url': sd.get('join_url', ''),
                        'start_datetime': sd['start_datetime'],
                        'end_datetime': sd['end_datetime'],
                        'capacity': sd['capacity'],
                    },
                )
                session_objects.append(session)
                if created:
                    self.ok(f'Session: {session.title}')

                # Register participants
                for learner in learners:
                    SessionParticipant.objects.get_or_create(
                        session=session, user=learner,
                        defaults={'status': 'attended' if sd['start_datetime'] < _now() else 'registered'},
                    )

            # ── 11. Virtual Classes ────────────────────────────────────────────
            self.log('\n[11] Virtual Classes...')
            vc_data = [
                {
                    'title': 'Classe Virtuelle Python Live',
                    'session': session_objects[0],
                    'provider': 'jitsi',
                    'join_url': 'https://meet.jit.si/lmspro-python-live',
                    'scheduled_start': session_objects[0].start_datetime,
                    'scheduled_end': session_objects[0].end_datetime,
                },
                {
                    'title': 'Webinaire Marketing — Live',
                    'session': session_objects[2],
                    'provider': 'zoom',
                    'join_url': 'https://zoom.us/j/1234567890',
                    'scheduled_start': session_objects[2].start_datetime,
                    'scheduled_end': session_objects[2].end_datetime,
                },
            ]
            for vcd in vc_data:
                VirtualClass.objects.get_or_create(
                    title=vcd['title'],
                    defaults={
                        'session': vcd['session'],
                        'company': company,
                        'provider': vcd['provider'],
                        'join_url': vcd['join_url'],
                        'scheduled_start': vcd['scheduled_start'],
                        'scheduled_end': vcd['scheduled_end'],
                        'created_by': trainer,
                    },
                )
            self.ok('Virtual Classes created')

            # ── 12. HR Analytics ───────────────────────────────────────────────
            self.log('\n[12] HR Analytics...')

            # Skills
            skill_objects = {}
            for sd in SKILLS_DATA:
                skill, _ = Skill.objects.get_or_create(
                    company=company, name=sd['name'],
                    defaults={'category': sd['category']},
                )
                skill_objects[sd['name']] = skill

            # CourseSkills: link skills to courses
            course_skill_map = {
                'Python pour la Data Science': ['Python', 'Data Science'],
                'Management d\'Équipe Agile': ['Scrum / Agile', 'Leadership'],
                'Marketing Digital & Réseaux Sociaux': ['SEO', 'Marketing de contenu', 'Google Ads'],
                'Excel Avancé & Power BI': ['Excel Avancé', 'Power BI'],
                'Communication Professionnelle': ['Communication orale', 'Rédaction professionnelle'],
            }
            for course in course_objects:
                skill_names = course_skill_map.get(course.title, [])
                for sname in skill_names:
                    if sname in skill_objects:
                        CourseSkill.objects.get_or_create(
                            course=course, skill=skill_objects[sname],
                            defaults={'level_gained': 2},
                        )
            self.ok('Skills & CourseSkills created')

            # Job Roles
            job_role_objects = {}
            skill_list = list(skill_objects.values())
            for jt in JOB_ROLES_DATA:
                jr, _ = JobRole.objects.get_or_create(
                    company=company, title=jt,
                )
                job_role_objects[jt] = jr
                # Add skill requirements
                for s in skill_list[:3]:
                    JobRoleSkillRequirement.objects.get_or_create(
                        job_role=jr, skill=s,
                        defaults={'required_level': random.randint(2, 4)},
                    )
            self.ok('Job Roles created')

            # Employee Skills
            for learner in learners:
                for skill in skill_list[:6]:
                    EmployeeSkill.objects.get_or_create(
                        user=learner, skill=skill,
                        defaults={
                            'level': random.randint(1, 4),
                            'source': 'self_assessment',
                        },
                    )
            self.ok('Employee Skills created')

            # Development Plans (PDI)
            if employee:
                plan, _ = IndividualDevelopmentPlan.objects.get_or_create(
                    user=employee,
                    period_start=_past_date(90),
                    period_end=_date(90),
                    defaults={
                        'created_by': hr_user,
                        'status': 'active',
                    },
                )
                objectives_data = [
                    {'description': 'Maîtriser Python niveau intermédiaire', 'skill': skill_objects.get('Python'), 'course': course_objects[0]},
                    {'description': 'Obtenir la certification Excel Avancé', 'skill': skill_objects.get('Excel Avancé'), 'course': course_objects[3]},
                    {'description': 'Améliorer la communication professionnelle', 'skill': skill_objects.get('Communication orale'), 'course': course_objects[4]},
                ]
                for od in objectives_data:
                    PDIObjective.objects.get_or_create(
                        plan=plan, description=od['description'],
                        defaults={
                            'skill': od.get('skill'),
                            'course': od.get('course'),
                            'target_date': _date(60),
                            'expected_result': 'Niveau 3 atteint',
                            'status': random.choice(['not_started', 'in_progress']),
                        },
                    )
            if student:
                plan2, _ = IndividualDevelopmentPlan.objects.get_or_create(
                    user=student,
                    period_start=_past_date(30),
                    period_end=_date(120),
                    defaults={
                        'created_by': hr_user,
                        'status': 'active',
                    },
                )
                PDIObjective.objects.get_or_create(
                    plan=plan2,
                    description='Finaliser le parcours Data Analyst',
                    defaults={
                        'course': course_objects[0],
                        'target_date': _date(90),
                        'status': 'in_progress',
                    },
                )
            self.ok('Development Plans (PDI) created')

            # 360 Campaigns
            if manager and employee:
                camp, _ = Evaluation360Campaign.objects.get_or_create(
                    company=company,
                    target_user=employee,
                    title='Evaluation 360 — Pierre Employé Q2 2026',
                    defaults={
                        'period_start': _past_date(30),
                        'period_end': _date(30),
                        'status': 'open',
                        'created_by': hr_user,
                    },
                )
                for evaluator, etype in [(employee, 'self'), (manager, 'manager'), (hr_user, 'hr')]:
                    if evaluator:
                        Evaluation360Response.objects.get_or_create(
                            campaign=camp, evaluator=evaluator, evaluator_type=etype,
                            defaults={
                                'overall_score': round(random.uniform(3.5, 5.0), 2),
                                'answers': {
                                    'competence': random.randint(3, 5),
                                    'communication': random.randint(3, 5),
                                    'teamwork': random.randint(3, 5),
                                },
                                'submitted_at': _past(5),
                            },
                        )
            self.ok('360 Campaigns created')

            # Training Budget
            for yr in [2025, 2026]:
                TrainingBudgetEntry.objects.get_or_create(
                    company=company, year=yr,
                    defaults={
                        'amount_allocated': 5000000,
                        'amount_spent': 3200000 if yr == 2025 else 1500000,
                        'notes': f'Budget formation annuel {yr}',
                    },
                )
            self.ok('Training Budgets created')

            # ── 13. Social ─────────────────────────────────────────────────────
            self.log('\n[13] Social...')

            # Forum Threads & Posts
            threads_data = [
                {
                    'author': student,
                    'course': course_objects[0],
                    'title': 'Question sur les DataFrames Pandas',
                    'posts': [
                        {'author': student, 'content': 'Comment filtrer un DataFrame par plusieurs conditions simultanées ?'},
                        {'author': trainer, 'content': 'Utilisez l\'opérateur & entre parenthèses : df[(df["col1"] > 0) & (df["col2"] == "valeur")]'},
                        {'author': employee, 'content': 'Merci ! Ça fonctionne parfaitement.', 'is_solution': False},
                    ],
                },
                {
                    'author': employee,
                    'course': course_objects[1],
                    'title': 'Différence entre Scrum Master et Product Owner',
                    'posts': [
                        {'author': employee, 'content': 'Quelqu\'un peut expliquer clairement les rôles dans Scrum ?'},
                        {'author': manager, 'content': 'Le Scrum Master facilite le processus, le PO gère le backlog et les priorités.', 'is_solution': True},
                    ],
                    'is_pinned': True,
                },
                {
                    'author': manager,
                    'company': company,
                    'title': 'Ressources recommandées pour le SEO en 2026',
                    'posts': [
                        {'author': manager, 'content': 'Quels outils gratuits utilisez-vous pour l\'audit SEO ?'},
                        {'author': trainer, 'content': 'Screaming Frog (version gratuite), Google Search Console et Ubersuggest sont excellents.'},
                    ],
                },
            ]
            for td in threads_data:
                thread, _ = ForumThread.objects.get_or_create(
                    title=td['title'],
                    defaults={
                        'author': td['author'],
                        'course': td.get('course'),
                        'company': td.get('company', company),
                        'is_pinned': td.get('is_pinned', False),
                    },
                )
                for pd in td.get('posts', []):
                    ForumPost.objects.get_or_create(
                        thread=thread, author=pd['author'], content=pd['content'][:50],
                        defaults={
                            'content': pd['content'],
                            'is_solution': pd.get('is_solution', False),
                        },
                    )
            self.ok('Forum Threads & Posts created')

            # Learning Groups
            group1, _ = LearningGroup.objects.get_or_create(
                name='Club Python LMS PRO',
                defaults={
                    'company': company,
                    'description': 'Groupe d\'apprentissage Python pour les passionnés de data.',
                    'created_by': trainer,
                },
            )
            group1.members.set([u for u in [trainer, employee, student, manager] if u])

            group2, _ = LearningGroup.objects.get_or_create(
                name='Managers Agiles',
                defaults={
                    'company': company,
                    'description': 'Partage de bonnes pratiques managériales agiles.',
                    'created_by': manager,
                },
            )
            if manager and hr_user:
                group2.members.set([u for u in [manager, hr_user, admin_user] if u])
            self.ok('Learning Groups created')

            # Mentorship
            if trainer and employee:
                MentorshipRelation.objects.get_or_create(
                    mentor=trainer, mentee=employee,
                    defaults={'status': 'active', 'started_at': _past_date(30), 'notes': 'Accompagnement Python & Data Science'},
                )
            if manager and student:
                MentorshipRelation.objects.get_or_create(
                    mentor=manager, mentee=student,
                    defaults={'status': 'active', 'started_at': _past_date(20), 'notes': 'Orientation professionnelle'},
                )
            self.ok('Mentorships created')

            # Conversations & Messages
            active_users = [u for u in [employee, student, trainer, manager] if u]
            if len(active_users) >= 2:
                conv, _ = Conversation.objects.get_or_create(
                    title='Discussion Python',
                    defaults={'is_group': True},
                )
                conv.participants.set(active_users[:3])
                messages_content = [
                    (active_users[0], 'Bonjour à tous ! Prêts pour la session Python de vendredi ?'),
                    (active_users[1], 'Oui, j\'ai préparé des exercices pratiques.'),
                    (active_users[0], 'Super ! Est-ce qu\'on va couvrir les DataFrames ?'),
                    (active_users[1] if len(active_users) > 1 else active_users[0], 'Absolument, et aussi les visualisations avec Matplotlib.'),
                ]
                for sender, content in messages_content:
                    Message.objects.get_or_create(
                        conversation=conv, sender=sender, content=content[:50],
                        defaults={'content': content},
                    )
                # Private conversation
                if trainer and employee:
                    priv_conv, _ = Conversation.objects.get_or_create(
                        title='',
                        defaults={'is_group': False},
                    )
                    priv_conv.participants.set([trainer, employee])
                    Message.objects.get_or_create(
                        conversation=priv_conv, sender=employee,
                        content='Bonjour Sophie, j\'ai une question sur l\'exercice pandas...'[:50],
                        defaults={'content': 'Bonjour Sophie, j\'ai une question sur l\'exercice pandas de la leçon 3.'},
                    )
            self.ok('Conversations & Messages created')

            # ── 14. Notifications ──────────────────────────────────────────────
            self.log('\n[14] Notifications...')
            all_users = list(users.values())
            notifs_templates = [
                {
                    'title': 'Nouvelle formation disponible',
                    'message': 'La formation "Communication Professionnelle" est maintenant accessible.',
                    'channel': 'in_app',
                    'status': 'sent',
                    'is_read': False,
                },
                {
                    'title': 'Rappel de session',
                    'message': 'Votre session de formation commence dans 24h. Préparez-vous !',
                    'channel': 'in_app',
                    'status': 'sent',
                    'is_read': True,
                },
                {
                    'title': 'Badge obtenu !',
                    'message': 'Félicitations ! Vous avez débloqué le badge "Premier Pas".',
                    'channel': 'in_app',
                    'status': 'sent',
                    'is_read': False,
                },
                {
                    'title': 'Quiz disponible',
                    'message': 'Un nouveau quiz est disponible pour le cours Python.',
                    'channel': 'in_app',
                    'status': 'sent',
                    'is_read': False,
                },
                {
                    'title': 'Certificat émis',
                    'message': 'Votre certificat de formation a été généré. Téléchargez-le !',
                    'channel': 'in_app',
                    'status': 'sent',
                    'is_read': True,
                },
            ]
            for u in all_users:
                # Notification preferences
                NotificationPreference.objects.get_or_create(
                    user=u,
                    defaults={
                        'email_enabled': True,
                        'sms_enabled': False,
                        'whatsapp_enabled': False,
                        'push_enabled': True,
                        'in_app_enabled': True,
                    },
                )
                # Create 3 notifications per user
                for nt in notifs_templates[:3]:
                    Notification.objects.get_or_create(
                        user=u, title=nt['title'],
                        defaults={
                            'message': nt['message'],
                            'channel': nt['channel'],
                            'status': nt['status'],
                            'is_read': nt['is_read'],
                            'sent_at': _past(random.randint(1, 10)),
                        },
                    )
            self.ok('Notifications created')

        # ── Summary ────────────────────────────────────────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('  seed_all completed!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'  Categories   : {Category.objects.count()}')
        self.stdout.write(f'  Courses      : {Course.objects.count()}')
        self.stdout.write(f'  Lessons      : {Lesson.objects.count()}')
        self.stdout.write(f'  Enrollments  : {Enrollment.objects.count()}')
        self.stdout.write(f'  Assessments  : {Assessment.objects.count()}')
        self.stdout.write(f'  Certificates : {Certificate.objects.count()}')
        self.stdout.write(f'  Badges       : {Badge.objects.count()}')
        self.stdout.write(f'  Sessions     : {TrainingSession.objects.count()}')
        self.stdout.write(f'  Notifications: {Notification.objects.count()}')
        self.stdout.write(self.style.SUCCESS('=' * 60))

    def _reset(self, *models):
        from apps.catalog.models import Category
        from apps.courses.models import Course
        from apps.assessments.models import Assessment, QuestionBank
        from apps.gamification.models import Level, Badge, Challenge
        from apps.learning_paths.models import LearningPath, TrainingSession
        from apps.certificates.models import Certificate, CertificateTemplate

        to_delete = [
            Certificate, CertificateTemplate,
            Challenge, Badge, Level,
            Assessment, QuestionBank,
            TrainingSession, LearningPath,
            Course, Category,
        ]
        for model in to_delete:
            count, _ = model.objects.all().delete()
            if count:
                self.warn(f'Deleted {count} {model.__name__}')
