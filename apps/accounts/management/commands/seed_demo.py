"""
Management command: seed_demo
Creates all demo accounts for each role so the login quick-connect buttons work.

Usage:
    python manage.py seed_demo
    python manage.py seed_demo --reset   # deletes demo users first then re-creates
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.constants import Roles


DEMO_PASSWORD = 'Demo@1234!'

DEMO_COMPANY = {
    'name': 'LMS PRO Demo',
    'sector': 'Formation',
    'country': 'Sénégal',
    'subscription_status': 'active',
}

TRAINING_CENTER_COMPANY = {
    'name': 'Tech Innovation Center',
    'sector': 'Formation',
    'country': 'Sénégal',
    'subscription_status': 'active',
}

DEMO_USERS = [
    {
        'email': 'superadmin@lmspro.com',
        'first_name': 'Super',
        'last_name': 'Admin',
        'role': Roles.SUPER_ADMIN,
        'job_title': 'Super Administrateur Plateforme',
        'is_superuser': True,
        'is_staff': True,
        'company': False,  # super_admin has no company
    },
    {
        'email': 'admin@lmspro.com',
        'first_name': 'Admin',
        'last_name': 'Entreprise',
        'role': Roles.COMPANY_ADMIN,
        'job_title': 'Administrateur Entreprise',
        'company': True,
    },
    {
        'email': 'hr@lmspro.com',
        'first_name': 'Marie',
        'last_name': 'Responsable RH',
        'role': Roles.HR,
        'job_title': 'Responsable Ressources Humaines',
        'company': True,
    },
    {
        'email': 'manager@lmspro.com',
        'first_name': 'Jean',
        'last_name': 'Manager',
        'role': Roles.MANAGER,
        'job_title': 'Chef de Projet',
        'company': True,
    },
    {
        'email': 'trainer@lmspro.com',
        'first_name': 'Sophie',
        'last_name': 'Formatrice',
        'role': Roles.TRAINER,
        'job_title': 'Formatrice Expert',
        'is_trainer_approved': True,
        'company': True,
    },
    {
        'email': 'employee@lmspro.com',
        'first_name': 'Pierre',
        'last_name': 'Employé',
        'role': Roles.EMPLOYEE,
        'job_title': 'Chargé de Communication',
        'company': True,
    },
    {
        'email': 'student@lmspro.com',
        'first_name': 'Fatou',
        'last_name': 'Apprenante',
        'role': Roles.STUDENT,
        'job_title': 'Étudiante',
        'company': False,
    },
    {
        'email': 'training_center_admin@lmspro.com',
        'first_name': 'Admin',
        'last_name': 'Centre Formation',
        'role': Roles.COMPANY_ADMIN,
        'job_title': 'Directeur Centre de Formation',
        'company': 'training_center',
    },
]


class Command(BaseCommand):
    help = 'Seed demo accounts for every role (for development/demo purposes)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing demo users before re-creating them',
        )

    def handle(self, *args, **options):
        from apps.accounts.models import User
        from apps.tenants.models import Company, Department, SubscriptionPlan

        reset = options['reset']

        if reset:
            deleted, _ = User.objects.filter(
                email__in=[u['email'] for u in DEMO_USERS]
            ).delete()
            self.stdout.write(self.style.WARNING(f'  [-] {deleted} demo user(s) deleted.'))

        with transaction.atomic():
            # ── Plan ──────────────────────────────────────────────────────────
            plan, _ = SubscriptionPlan.objects.get_or_create(
                code='enterprise',
                defaults={
                    'name': 'Enterprise',
                    'price': 0,
                    'max_users': 9999,
                    'max_storage_gb': 100,
                    'features': {
                        'modules': 'all',
                        'support': '24/7',
                        'api_access': True,
                    },
                },
            )

            # ── Company (entreprise) ───────────────────────────────────────────
            company, created = Company.objects.get_or_create(
                slug='lmspro-demo',
                defaults={**DEMO_COMPANY, 'plan': plan},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  [+] Company created: {company.name}'))
            else:
                self.stdout.write(f'  [=] Company already exists: {company.name}')

            # ── Company (centre de formation) ─────────────────────────────────
            training_center, created_tc = Company.objects.get_or_create(
                slug='tech-innovation-center',
                defaults={**TRAINING_CENTER_COMPANY, 'plan': plan},
            )
            if created_tc:
                self.stdout.write(self.style.SUCCESS(f'  [+] Company created: {training_center.name}'))
            else:
                self.stdout.write(f'  [=] Company already exists: {training_center.name}')

            # ── Department ────────────────────────────────────────────────────
            dept, _ = Department.objects.get_or_create(
                company=company,
                name='Direction Générale',
                defaults={'code': 'DG'},
            )
            tc_dept, _ = Department.objects.get_or_create(
                company=training_center,
                name='Direction',
                defaults={'code': 'DIR'},
            )

            # ── Users ─────────────────────────────────────────────────────────
            company_map = {True: company, False: None, 'training_center': training_center}
            dept_map = {True: dept, False: None, 'training_center': tc_dept}

            for data in DEMO_USERS:
                data = dict(data)
                email = data['email']
                company_key = data.pop('company', True)
                is_superuser = data.pop('is_superuser', False)
                is_staff = data.pop('is_staff', False)
                is_trainer_approved = data.pop('is_trainer_approved', False)

                if User.objects.filter(email=email).exists():
                    user = User.objects.get(email=email)
                    self.stdout.write(f'  [=] Already exists: {email} [{user.role}]')
                    continue

                user = User.objects.create_user(
                    email=email,
                    password=DEMO_PASSWORD,
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    role=data['role'],
                    job_title=data.get('job_title', ''),
                    company=company_map[company_key],
                    department=dept_map[company_key],
                    is_superuser=is_superuser,
                    is_staff=is_staff,
                    is_active=True,
                    is_trainer_approved=is_trainer_approved,
                )
                self.stdout.write(
                    self.style.SUCCESS(f'  [+] Created: {email} [{user.role}]')
                )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('-' * 60))
        self.stdout.write(self.style.SUCCESS('  Demo accounts ready! Login credentials:'))
        self.stdout.write(self.style.SUCCESS('-' * 60))
        for u in DEMO_USERS:
            self.stdout.write(f"  {u['role']:20s}  {u['email']:35s}  {DEMO_PASSWORD}")
        self.stdout.write(self.style.SUCCESS('-' * 60))
