"""
Management command: seed_hr
Seeds rich HR & Competences data for all active companies:
  - Skills (company-specific catalogue)
  - JobRoles + SkillRequirements
  - EmployeeSkills (level 0-5 per skill)
  - IndividualDevelopmentPlans + PDIObjectives
  - Evaluation360 campaigns (with self / manager / peer / hr / final responses)
  - Auto-evaluation scores computed from real learning data
  - TrainingBudgetEntries (3 years)

Run:
    python manage.py seed_hr
    python manage.py seed_hr --company <id>   # single company
    python manage.py seed_hr --reset          # wipe HR data first
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


SKILLS_BY_CATEGORY = {
    'Techniques Métier': [
        'Comptabilité Générale', 'Contrôle de Gestion', 'Analyse Financière',
        'Audit Interne', 'Gestion de Trésorerie', 'Reporting Financier',
        'Développement Python', 'Développement JavaScript', 'Architecture Logicielle',
        'Administration Cloud (AWS)', 'Cybersécurité Réseau', 'DevOps & CI/CD',
        'Gestion de Production', 'Maintenance Industrielle', 'Contrôle Qualité ISO',
        'Gestion Supply Chain', 'Ingénierie Pédagogique', 'Digital Learning',
        'Soins Infirmiers', 'Pharmacologie Clinique', 'Gestion Hospitalière',
        'Recrutement & Talent', 'Gestion de Paie', 'Droit du Travail',
    ],
    'Management': [
        'Leadership Stratégique', 'Management d\'Équipe', 'Coaching Professionnel',
        'Conduite du Changement', 'Prise de Décision', 'Gestion de Conflits',
        'Planification Stratégique', 'Gestion de Projet Agile', 'Négociation Avancée',
        'Intelligence Émotionnelle', 'Management à Distance', 'Délégation Efficace',
    ],
    'Communication': [
        'Communication Orale', 'Communication Écrite', 'Prise de Parole en Public',
        'Animation de Réunion', 'Écriture Professionnelle', 'Anglais des Affaires',
        'Présentation PowerPoint', 'Communication Interculturelle',
    ],
    'Transversales': [
        'Gestion du Temps', 'Résolution de Problèmes', 'Créativité & Innovation',
        'Adaptabilité', 'Travail en Équipe', 'Orientation Résultats',
        'Sens du Service Client', 'Organisation & Rigueur', 'Curiosité Intellectuelle',
    ],
    'Outils & Technologies': [
        'Microsoft Excel Avancé', 'Power BI', 'SAP ERP', 'Salesforce CRM',
        'Google Workspace', 'Tableau de Bord RH', 'SIRH (Logiciel RH)',
    ],
}

JOB_ROLES_DEF = [
    {
        'title': 'Analyste Senior',
        'skills': ['Analyse Financière', 'Reporting Financier', 'Microsoft Excel Avancé', 'Communication Écrite'],
        'levels': [4, 3, 3, 3],
    },
    {
        'title': 'Chef de Projet',
        'skills': ['Gestion de Projet Agile', 'Management d\'Équipe', 'Communication Orale', 'Prise de Décision'],
        'levels': [4, 3, 4, 3],
    },
    {
        'title': 'Responsable Département',
        'skills': ['Leadership Stratégique', 'Management d\'Équipe', 'Planification Stratégique', 'Négociation Avancée'],
        'levels': [4, 4, 3, 3],
    },
    {
        'title': 'Coordinateur RH',
        'skills': ['Recrutement & Talent', 'Gestion de Paie', 'Droit du Travail', 'Communication Orale'],
        'levels': [3, 3, 3, 3],
    },
    {
        'title': 'Expert Technique',
        'skills': ['Cybersécurité Réseau', 'Architecture Logicielle', 'DevOps & CI/CD', 'Gestion du Temps'],
        'levels': [4, 4, 3, 3],
    },
    {
        'title': 'Manager d\'Équipe',
        'skills': ['Management d\'Équipe', 'Coaching Professionnel', 'Intelligence Émotionnelle', 'Gestion de Conflits'],
        'levels': [4, 3, 4, 3],
    },
    {
        'title': 'Consultant Senior',
        'skills': ['Analyse Financière', 'Présentation PowerPoint', 'Anglais des Affaires', 'Conduite du Changement'],
        'levels': [3, 4, 3, 3],
    },
]

PDI_OBJECTIVE_TEMPLATES = [
    ('Atteindre le niveau Expert en {skill}', 'Valider par une certification ou un projet terrain'),
    ('Développer la compétence {skill} via une formation certifiante', 'Score > 80% au quiz de validation'),
    ('Améliorer le niveau en {skill} (de {current}/5 à {target}/5)', 'Évaluation manager en fin de trimestre'),
    ('Prendre en charge un projet impliquant {skill}', 'Livraison documentée du projet'),
    ('Mentorer un collègue sur {skill}', 'Retour positif du mentoré et du manager'),
]

EVAL_DIMENSIONS = [
    'competences_metier', 'qualite_travail', 'cooperation', 'initiative',
    'communication', 'respect_delais', 'adaptabilite', 'orientation_client',
]

EVAL_COMMENTS = [
    'Très bon niveau global, efforts constants et résultats visibles.',
    'Progression notable sur ce semestre, bonne intégration au sein de l\'équipe.',
    'Points forts en communication, à renforcer sur la gestion de projet.',
    'Collaborateur fiable, mérite d\'être plus mis en avant pour des responsabilités nouvelles.',
    'Des marges de progression restent possibles sur l\'autonomie et l\'initiative.',
    'Excellente maîtrise technique, gagne à partager ses connaissances.',
    'Engagement exemplaire, un véritable moteur pour l\'équipe.',
    'Quelques difficultés sur les délais mais la qualité du travail reste bonne.',
]


class Command(BaseCommand):
    help = 'Seeds rich HR & Competences data for all active companies'

    def add_arguments(self, parser):
        parser.add_argument('--company', type=int, help='Seed only this company id')
        parser.add_argument('--reset', action='store_true', help='Wipe HR data before seeding')

    def handle(self, *args, **options):
        from apps.tenants.models import Company

        if options['reset']:
            self._reset(options.get('company'))

        companies = (
            [Company.objects.get(pk=options['company'])]
            if options.get('company')
            else list(Company.objects.filter(is_active=True))
        )

        self.stdout.write(f'\n=== SEED HR ({len(companies)} companies) ===\n')

        for company in companies:
            self.stdout.write(f'\n>> {company.name}')
            with transaction.atomic():
                skills = self._seed_skills(company)
                job_roles = self._seed_job_roles(company, skills)
                courses = self._get_courses(company)
                users = self._get_users(company)
                if not users:
                    self.stdout.write('   (no users, skipping)')
                    continue
                self._seed_employee_skills(users, skills)
                self._seed_pdi_plans(company, users, skills, courses)
                self._seed_evaluations(company, users)
                self._seed_budgets(company)
                self._seed_permission_codes()

        self.stdout.write(self.style.SUCCESS('\nHR seed complete!\n'))

    # -----------------------------------------------------------------------

    def _reset(self, company_id=None):
        from apps.hr_analytics.models import (
            Skill, JobRole, EmployeeSkill, IndividualDevelopmentPlan, Evaluation360Campaign, TrainingBudgetEntry,
        )
        self.stdout.write('Resetting HR data...')
        qs_filter = {'company_id': company_id} if company_id else {}
        Evaluation360Campaign.objects.filter(**qs_filter).delete()
        IndividualDevelopmentPlan.objects.filter(user__company_id=company_id).delete() if company_id else IndividualDevelopmentPlan.objects.all().delete()
        EmployeeSkill.objects.filter(user__company_id=company_id).delete() if company_id else EmployeeSkill.objects.all().delete()
        JobRole.objects.filter(**qs_filter).delete()
        Skill.objects.filter(**qs_filter).delete()
        TrainingBudgetEntry.objects.filter(**qs_filter).delete()
        self.stdout.write('  Done.')

    # -----------------------------------------------------------------------

    def _seed_skills(self, company):
        from apps.hr_analytics.models import Skill
        created = 0
        all_skills = []
        for category, names in SKILLS_BY_CATEGORY.items():
            for name in names:
                skill, is_new = Skill.objects.get_or_create(
                    company=company, name=name,
                    defaults={'category': category},
                )
                if is_new:
                    created += 1
                all_skills.append(skill)
        self.stdout.write(f'   Skills: {len(all_skills)} ({created} created)')
        return all_skills

    def _seed_job_roles(self, company, all_skills):
        from apps.hr_analytics.models import JobRole, JobRoleSkillRequirement, Skill
        skill_map = {s.name: s for s in all_skills}
        roles = []
        req_count = 0
        for defn in JOB_ROLES_DEF:
            role, _ = JobRole.objects.get_or_create(company=company, title=defn['title'])
            for skill_name, level in zip(defn['skills'], defn['levels']):
                skill = skill_map.get(skill_name)
                if skill:
                    JobRoleSkillRequirement.objects.get_or_create(
                        job_role=role, skill=skill,
                        defaults={'required_level': level},
                    )
                    req_count += 1
            roles.append(role)
        self.stdout.write(f'   JobRoles: {len(roles)} | Requirements: {req_count}')
        return roles

    def _get_courses(self, company):
        from apps.courses.models import Course
        courses = list(Course.objects.filter(status='published'))
        return courses

    def _get_users(self, company):
        from apps.accounts.models import User
        return list(User.objects.filter(company=company).select_related('department', 'manager'))

    # -----------------------------------------------------------------------

    def _seed_employee_skills(self, users, all_skills):
        from apps.hr_analytics.models import EmployeeSkill
        from apps.progression.models import LessonProgress
        from apps.assessments.models import AssessmentAttempt

        created = 0
        for user in users:
            # Compute real skill level from learning data
            total_lessons = LessonProgress.objects.filter(user=user).count()
            done_lessons = LessonProgress.objects.filter(user=user, is_completed=True).count()
            completion_rate = (done_lessons / total_lessons) if total_lessons > 0 else 0

            attempts = list(AssessmentAttempt.objects.filter(user=user, status='graded'))
            avg_score = (sum(float(a.score or 0) for a in attempts) / len(attempts)) if attempts else 0

            # Base level from learning performance
            base_level = 1
            if completion_rate >= 0.8 and avg_score >= 80:
                base_level = 4
            elif completion_rate >= 0.6 and avg_score >= 65:
                base_level = 3
            elif completion_rate >= 0.3:
                base_level = 2

            # Assign 5-10 skills per user with individual variance
            n_skills = random.randint(5, 10)
            chosen = random.sample(all_skills, min(n_skills, len(all_skills)))
            for skill in chosen:
                variance = random.randint(-1, 1)
                level = max(0, min(5, base_level + variance))
                _, is_new = EmployeeSkill.objects.get_or_create(
                    user=user, skill=skill,
                    defaults={
                        'level': level,
                        'source': EmployeeSkill.SOURCE_AUTO,
                    },
                )
                if is_new:
                    created += 1

        self.stdout.write(f'   EmployeeSkills: {created} created')

    # -----------------------------------------------------------------------

    def _seed_pdi_plans(self, company, users, skills, courses):
        from apps.hr_analytics.models import IndividualDevelopmentPlan, PDIObjective, EmployeeSkill
        from apps.accounts.models import User
        from apps.core.constants import Roles

        hr_users = [u for u in users if u.role in (Roles.HR, Roles.COMPANY_ADMIN)] or [users[0]]
        managers = [u for u in users if u.role == Roles.MANAGER] or [users[0]]
        employees = [u for u in users if u.role == Roles.EMPLOYEE]

        if not employees:
            self.stdout.write('   PDI plans: 0 | Objectives: 0 (no employees)')
            return

        # 60% of employees get a PDI
        n_target = min(max(1, int(len(employees) * 0.60)), len(employees))
        target_users = random.sample(employees, n_target)
        created_plans = 0
        created_objs = 0

        for user in target_users:
            creator = user.manager or random.choice(hr_users)
            plan, created = IndividualDevelopmentPlan.objects.get_or_create(
                user=user,
                period_start=_date_past(180),
                defaults={
                    'created_by': creator,
                    'period_end': _date_future(180),
                    'status': random.choice([
                        'active', 'active', 'active', 'completed', 'draft',
                    ]),
                },
            )
            if not created:
                continue
            created_plans += 1

            # 2-4 objectives mixing skills and courses
            user_skills = list(EmployeeSkill.objects.filter(user=user).select_related('skill'))
            n_obj = random.randint(2, 4)
            for _ in range(n_obj):
                tpl_title, tpl_result = random.choice(PDI_OBJECTIVE_TEMPLATES)
                emp_skill = random.choice(user_skills) if user_skills else None
                skill = emp_skill.skill if emp_skill else random.choice(skills) if skills else None
                current = emp_skill.level if emp_skill else 1
                target = min(5, current + random.randint(1, 2))

                description = tpl_title.format(
                    skill=skill.name if skill else 'domaine métier',
                    current=current, target=target,
                )
                PDIObjective.objects.create(
                    plan=plan,
                    skill=skill,
                    course=random.choice(courses) if courses and random.random() < 0.5 else None,
                    description=description,
                    target_date=_date_future(random.randint(30, 150)),
                    expected_result=tpl_result,
                    status=random.choice([
                        'not_started', 'in_progress', 'in_progress', 'achieved',
                    ]),
                )
                created_objs += 1

        self.stdout.write(f'   PDI plans: {created_plans} | Objectives: {created_objs}')

    # -----------------------------------------------------------------------

    def _seed_evaluations(self, company, users):
        from apps.hr_analytics.models import (
            Evaluation360Campaign, Evaluation360Response, EmployeeSkill,
        )
        from apps.accounts.models import User
        from apps.core.constants import Roles
        from apps.progression.models import LessonProgress
        from apps.assessments.models import AssessmentAttempt
        from apps.learning_paths.models import SessionParticipant
        from apps.gamification.models import XPLog, UserStreak

        hr_users = [u for u in users if u.role in (Roles.HR, Roles.COMPANY_ADMIN)] or [users[0]]
        managers = [u for u in users if u.role == Roles.MANAGER] or [users[0]]
        employees = [u for u in users if u.role == Roles.EMPLOYEE]
        peers = employees  # use for peer evaluations

        if not employees:
            self.stdout.write('   Evaluations 360: 0 campaigns | 0 responses (no employees)')
            return

        # Evaluate 50% of employees
        n_target = min(max(1, int(len(employees) * 0.50)), len(employees))
        target_employees = random.sample(employees, n_target)
        created_campaigns = 0
        created_responses = 0

        for user in target_employees:
            # ── Compute overall score from real data ──
            total_lessons = LessonProgress.objects.filter(user=user).count()
            done_lessons = LessonProgress.objects.filter(user=user, is_completed=True).count()
            completion_rate = (done_lessons / total_lessons * 100) if total_lessons > 0 else 0

            attempts = list(AssessmentAttempt.objects.filter(user=user, status='graded'))
            avg_score = (sum(float(a.score or 0) for a in attempts) / len(attempts)) if attempts else 0

            total_sessions = SessionParticipant.objects.filter(user=user).exclude(status='cancelled').count()
            attended = SessionParticipant.objects.filter(user=user, status='attended').count()
            attendance_rate = (attended / total_sessions * 100) if total_sessions > 0 else 50

            xp_total = sum(x.amount for x in XPLog.objects.filter(user=user))
            try:
                streak = user.streak.current_streak
            except Exception:
                streak = random.randint(0, 20)

            assiduity = min(100, (min(100, xp_total / 10) * 0.5 + min(100, streak * 5) * 0.5))
            overall = round(
                completion_rate * 0.40 + avg_score * 0.35 + attendance_rate * 0.15 + assiduity * 0.10,
                2
            )
            overall = min(100, max(10, overall))

            # ── Create campaign ──
            hr = random.choice(hr_users)
            campaign, is_new = Evaluation360Campaign.objects.get_or_create(
                company=company,
                target_user=user,
                title=f'Evaluation 360 - {user.get_full_name()} - S1 2026',
                defaults={
                    'period_start': _date_past(90),
                    'period_end': _date_past(1),
                    'status': Evaluation360Campaign.STATUS_CLOSED,
                    'created_by': hr,
                },
            )
            if not is_new:
                continue
            created_campaigns += 1

            def make_answers(base):
                score = max(10, min(100, base))
                return {
                    dim: round(score * random.uniform(0.80, 1.12), 1)
                    for dim in EVAL_DIMENSIONS
                } | {'overall_comment': random.choice(EVAL_COMMENTS)}

            # Self evaluation (slightly optimistic)
            Evaluation360Response.objects.get_or_create(
                campaign=campaign, evaluator=user,
                evaluator_type=Evaluation360Response.EVALUATOR_SELF,
                defaults={
                    'answers': make_answers(overall * 1.05),
                    'overall_score': Decimal(str(round(min(100, overall * 1.05), 2))),
                    'submitted_at': _past(random.randint(5, 20)),
                },
            )
            created_responses += 1

            # Manager evaluation
            mgr = user.manager or (random.choice(managers) if managers else None)
            if mgr:
                Evaluation360Response.objects.get_or_create(
                    campaign=campaign, evaluator=mgr,
                    evaluator_type=Evaluation360Response.EVALUATOR_MANAGER,
                    defaults={
                        'answers': make_answers(overall),
                        'overall_score': Decimal(str(round(overall, 2))),
                        'submitted_at': _past(random.randint(3, 15)),
                    },
                )
                created_responses += 1

            # 1-2 peer evaluations
            available_peers = [p for p in peers if p.id != user.id and p.id != (mgr.id if mgr else -1)]
            for peer in random.sample(available_peers, min(2, len(available_peers))):
                peer_score = round(overall * random.uniform(0.88, 1.08), 2)
                try:
                    Evaluation360Response.objects.get_or_create(
                        campaign=campaign, evaluator=peer,
                        evaluator_type=Evaluation360Response.EVALUATOR_PEER,
                        defaults={
                            'answers': make_answers(peer_score),
                            'overall_score': Decimal(str(round(min(100, peer_score), 2))),
                            'submitted_at': _past(random.randint(2, 12)),
                        },
                    )
                    created_responses += 1
                except Exception:
                    pass

            # HR evaluation
            Evaluation360Response.objects.get_or_create(
                campaign=campaign, evaluator=hr,
                evaluator_type=Evaluation360Response.EVALUATOR_HR,
                defaults={
                    'answers': make_answers(overall * 0.97),
                    'overall_score': Decimal(str(round(min(100, overall * 0.97), 2))),
                    'submitted_at': _past(random.randint(1, 7)),
                },
            )
            created_responses += 1

            # Final consolidated evaluation
            Evaluation360Response.objects.get_or_create(
                campaign=campaign, evaluator=hr,
                evaluator_type=Evaluation360Response.EVALUATOR_FINAL,
                defaults={
                    'answers': make_answers(overall),
                    'overall_score': Decimal(str(overall)),
                    'submitted_at': _past(0),
                },
            )
            created_responses += 1

            # Update employee skill levels based on overall score
            boost = 1 if overall >= 70 else (0 if overall >= 45 else -1)
            if boost != 0:
                from apps.hr_analytics.models import EmployeeSkill
                for es in EmployeeSkill.objects.filter(user=user):
                    new_level = max(0, min(5, es.level + boost))
                    if new_level != es.level:
                        EmployeeSkill.objects.filter(pk=es.pk).update(
                            level=new_level, source=EmployeeSkill.SOURCE_AUTO
                        )

        self.stdout.write(f'   Evaluations 360: {created_campaigns} campaigns | {created_responses} responses')

    # -----------------------------------------------------------------------

    def _seed_budgets(self, company):
        from apps.hr_analytics.models import TrainingBudgetEntry
        count = 0
        for year in [2024, 2025, 2026]:
            base_budget = random.randint(8_000_000, 60_000_000)
            pct_spent = random.uniform(0.40, 0.90)
            spent = int(base_budget * pct_spent)
            _, created = TrainingBudgetEntry.objects.get_or_create(
                company=company, year=year,
                defaults={
                    'amount_allocated': Decimal(str(base_budget)),
                    'amount_spent': Decimal(str(spent)),
                    'notes': (
                        f'Budget formation {year}. Inclut formations externes ({int(pct_spent*70)}%), '
                        f'e-learning ({int(pct_spent*20)}%) et certifications ({int(pct_spent*10)}%).'
                    ),
                },
            )
            if created:
                count += 1
        self.stdout.write(f'   BudgetEntries: {count} created')

    # -----------------------------------------------------------------------

    def _seed_permission_codes(self):
        """Seed PermissionCode entries used by the Roles & Permissions module."""
        from apps.accounts.models import PermissionCode

        PERMISSIONS = [
            # (code, label, category)
            # Cours
            ('course.view',    'Voir les formations',         'Formations'),
            ('course.enroll',  'S\'inscrire aux formations',  'Formations'),
            ('course.create',  'Créer des formations',        'Formations'),
            ('course.edit',    'Modifier des formations',     'Formations'),
            ('course.delete',  'Supprimer des formations',    'Formations'),
            ('course.publish', 'Publier des formations',      'Formations'),
            # Sessions
            ('session.view',     'Voir les sessions',           'Sessions'),
            ('session.register', 'S\'inscrire aux sessions',    'Sessions'),
            ('session.create',   'Créer des sessions',          'Sessions'),
            ('session.edit',     'Modifier des sessions',       'Sessions'),
            ('session.delete',   'Supprimer des sessions',      'Sessions'),
            # Évaluations
            ('assessment.view',   'Voir les évaluations',        'Évaluations'),
            ('assessment.take',   'Passer les évaluations',      'Évaluations'),
            ('assessment.create', 'Créer des évaluations',       'Évaluations'),
            ('assessment.grade',  'Noter les évaluations',       'Évaluations'),
            # RH
            ('hr.view_team',     'Voir l\'équipe',              'RH'),
            ('hr.manage_skills', 'Gérer les compétences',       'RH'),
            ('hr.manage_pdi',    'Gérer les plans de développement', 'RH'),
            ('hr.evaluate_360',  'Lancer des évaluations 360°', 'RH'),
            ('hr.view_budgets',  'Voir les budgets formation',  'RH'),
            ('hr.manage_budgets','Gérer les budgets formation', 'RH'),
            # Utilisateurs
            ('user.view',        'Voir les utilisateurs',       'Utilisateurs'),
            ('user.create',      'Créer des utilisateurs',      'Utilisateurs'),
            ('user.edit',        'Modifier des utilisateurs',   'Utilisateurs'),
            ('user.deactivate',  'Désactiver des utilisateurs', 'Utilisateurs'),
            ('user.assign_role', 'Attribuer des rôles',         'Utilisateurs'),
            # Administration
            ('admin.view_logs',      'Voir les journaux d\'audit',    'Administration'),
            ('admin.manage_company', 'Gérer les paramètres entreprise','Administration'),
            ('admin.manage_roles',   'Gérer les rôles et permissions', 'Administration'),
            # Rapports
            ('report.view_hr',    'Voir les rapports RH',         'Rapports'),
            ('report.export',     'Exporter les rapports',        'Rapports'),
            ('report.view_exec',  'Voir le tableau de bord exécutif', 'Rapports'),
            # Classes virtuelles
            ('vclass.view',   'Voir les classes virtuelles',   'Classes Virtuelles'),
            ('vclass.join',   'Rejoindre une classe virtuelle','Classes Virtuelles'),
            ('vclass.create', 'Créer des classes virtuelles',  'Classes Virtuelles'),
            # Gamification
            ('gamif.view',   'Voir les récompenses',    'Gamification'),
            ('gamif.manage', 'Gérer la gamification',   'Gamification'),
        ]

        from apps.accounts.models import RolePermission
        from apps.core.constants import Roles

        # Default role-permission mapping
        DEFAULT_GRANTS = {
            Roles.SUPER_ADMIN:   [p[0] for p in PERMISSIONS],  # all
            Roles.COMPANY_ADMIN: [p[0] for p in PERMISSIONS if not p[0].startswith('admin.manage_roles')],
            Roles.HR: [
                'course.view', 'course.enroll', 'course.create', 'course.edit', 'course.publish',
                'session.view', 'session.register', 'session.create', 'session.edit',
                'assessment.view', 'assessment.take', 'assessment.create', 'assessment.grade',
                'hr.view_team', 'hr.manage_skills', 'hr.manage_pdi', 'hr.evaluate_360',
                'hr.view_budgets', 'hr.manage_budgets',
                'user.view', 'user.create', 'user.edit',
                'report.view_hr', 'report.export',
                'vclass.view', 'vclass.join', 'vclass.create',
                'gamif.view',
            ],
            Roles.MANAGER: [
                'course.view', 'course.enroll',
                'session.view', 'session.register',
                'assessment.view', 'assessment.take',
                'hr.view_team', 'hr.manage_pdi',
                'user.view',
                'report.view_hr',
                'vclass.view', 'vclass.join',
                'gamif.view',
            ],
            Roles.TRAINER: [
                'course.view', 'course.enroll', 'course.create', 'course.edit', 'course.publish',
                'session.view', 'session.register', 'session.create', 'session.edit',
                'assessment.view', 'assessment.take', 'assessment.create', 'assessment.grade',
                'vclass.view', 'vclass.join', 'vclass.create',
                'gamif.view',
            ],
            Roles.EMPLOYEE: [
                'course.view', 'course.enroll',
                'session.view', 'session.register',
                'assessment.view', 'assessment.take',
                'hr.view_team',
                'vclass.view', 'vclass.join',
                'gamif.view',
            ],
            Roles.STUDENT: [
                'course.view', 'course.enroll',
                'session.view', 'session.register',
                'assessment.view', 'assessment.take',
                'vclass.view', 'vclass.join',
                'gamif.view',
            ],
        }

        perm_count = 0
        for code, label, category in PERMISSIONS:
            perm, _ = PermissionCode.objects.get_or_create(
                code=code, defaults={'label': label, 'category': category},
            )
            perm_count += 1

        rp_count = 0
        for role, codes in DEFAULT_GRANTS.items():
            for code in codes:
                try:
                    perm = PermissionCode.objects.get(code=code)
                    RolePermission.objects.get_or_create(role=role, permission=perm)
                    rp_count += 1
                except PermissionCode.DoesNotExist:
                    pass

        self.stdout.write(f'   PermissionCodes: {perm_count} | RolePermissions: {rp_count}')

        # ── Seed RoleDefinitions (system roles) ───────────────────────────────
        from apps.accounts.models import RoleDefinition
        from apps.core.constants import Roles

        system_roles = [
            (Roles.SUPER_ADMIN,   'Super Administrateur',       'red'),
            (Roles.COMPANY_ADMIN, "Administrateur d'entreprise", 'violet'),
            (Roles.HR,            'Ressources Humaines',         'sky'),
            (Roles.MANAGER,       'Manager',                     'amber'),
            (Roles.EMPLOYEE,      'Employé',                     'emerald'),
            (Roles.TRAINER,       'Formateur',                   'indigo'),
            (Roles.STUDENT,       'Apprenant',                   'slate'),
        ]
        rd_count = 0
        for key, label, color in system_roles:
            _, created = RoleDefinition.objects.get_or_create(
                key=key,
                defaults={'label': label, 'color': color, 'is_system': True},
            )
            if created:
                rd_count += 1
        self.stdout.write(f'   RoleDefinitions: {rd_count} created')
