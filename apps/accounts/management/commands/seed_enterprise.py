"""
Management command: seed_enterprise
Creates 1 parent company + 5 subsidiaries with 100+ employees each,
seeding all modules with enriched data and computing auto-evaluation scores.

Usage:
    python manage.py seed_enterprise
    python manage.py seed_enterprise --reset   # wipe and re-create
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now():
    return timezone.now()


def _days(n):
    return _now() + timedelta(days=n)


def _past(n):
    return _now() - timedelta(days=n)


def _date_past(n):
    return date.today() - timedelta(days=n)


def _date_future(n):
    return date.today() + timedelta(days=n)


# ---------------------------------------------------------------------------
# Company & subsidiary definitions
# ---------------------------------------------------------------------------

PARENT_COMPANY = {
    'name': 'Groupe Nexus International',
    'legal_name': 'NEXUS INTERNATIONAL SAS',
    'sector': 'Holding',
    'country': 'Côte d\'Ivoire',
    'address': 'Plateau, Avenue Général de Gaulle, Abidjan',
    'phone': '+225 27 20 30 40 50',
    'email': 'contact@nexus-international.ci',
    'website': 'https://nexus-international.ci',
}

SUBSIDIARIES = [
    {
        'name': 'Nexus Finance & Conseil',
        'legal_name': 'NEXUS FINANCE ET CONSEIL SARL',
        'sector': 'Finance & Conseil',
        'country': 'Côte d\'Ivoire',
        'address': 'Zone 4, Boulevard de la Paix, Abidjan',
        'phone': '+225 27 21 30 40 51',
        'email': 'contact@nexus-finance.ci',
        'website': 'https://nexus-finance.ci',
        'slug_prefix': 'finance',
        'focus': 'finance',
    },
    {
        'name': 'Nexus Technologies',
        'legal_name': 'NEXUS TECHNOLOGIES SA',
        'sector': 'Technologies de l\'Information',
        'country': 'Côte d\'Ivoire',
        'address': 'Cocody, Rue des Jardins, Abidjan',
        'phone': '+225 27 22 30 40 52',
        'email': 'contact@nexus-tech.ci',
        'website': 'https://nexus-tech.ci',
        'slug_prefix': 'tech',
        'focus': 'tech',
    },
    {
        'name': 'Nexus Industries',
        'legal_name': 'NEXUS INDUSTRIES SA',
        'sector': 'Industrie & Production',
        'country': 'Côte d\'Ivoire',
        'address': 'Zone Industrielle, Port-Bouët, Abidjan',
        'phone': '+225 27 23 30 40 53',
        'email': 'contact@nexus-industries.ci',
        'website': 'https://nexus-industries.ci',
        'slug_prefix': 'industrie',
        'focus': 'industrie',
    },
    {
        'name': 'Nexus Formation & RH',
        'legal_name': 'NEXUS FORMATION ET RH SARL',
        'sector': 'Formation & Ressources Humaines',
        'country': 'Côte d\'Ivoire',
        'address': 'Marcory, Rue du Commerce, Abidjan',
        'phone': '+225 27 24 30 40 54',
        'email': 'contact@nexus-formation.ci',
        'website': 'https://nexus-formation.ci',
        'slug_prefix': 'formation',
        'focus': 'rh',
    },
    {
        'name': 'Nexus Santé & Services',
        'legal_name': 'NEXUS SANTE ET SERVICES SARL',
        'sector': 'Santé & Services',
        'country': 'Côte d\'Ivoire',
        'address': 'Yopougon, Rue des Hôpitaux, Abidjan',
        'phone': '+225 27 25 30 40 55',
        'email': 'contact@nexus-sante.ci',
        'website': 'https://nexus-sante.ci',
        'slug_prefix': 'sante',
        'focus': 'sante',
    },
]

# Departments per focus type
DEPARTMENTS_BY_FOCUS = {
    'finance': [
        ('Direction Générale', 'DG'),
        ('Finance & Comptabilité', 'FIN'),
        ('Audit & Contrôle', 'AUD'),
        ('Ressources Humaines', 'RH'),
        ('Informatique', 'IT'),
        ('Juridique & Conformité', 'JUR'),
    ],
    'tech': [
        ('Direction Générale', 'DG'),
        ('Développement Logiciel', 'DEV'),
        ('Infrastructure & Cloud', 'INFRA'),
        ('Cybersécurité', 'SEC'),
        ('Ressources Humaines', 'RH'),
        ('Product Management', 'PM'),
    ],
    'industrie': [
        ('Direction Générale', 'DG'),
        ('Production & Fabrication', 'PROD'),
        ('Qualité & Contrôle', 'QC'),
        ('Maintenance', 'MAINT'),
        ('Ressources Humaines', 'RH'),
        ('Logistique & Supply Chain', 'LOG'),
    ],
    'rh': [
        ('Direction Générale', 'DG'),
        ('Ingénierie de Formation', 'IF'),
        ('Développement RH', 'DRH'),
        ('Recrutement & Talents', 'REC'),
        ('Paie & Administration', 'ADM'),
        ('Digital Learning', 'DL'),
    ],
    'sante': [
        ('Direction Générale', 'DG'),
        ('Soins Médicaux', 'SOIN'),
        ('Administration Hospitalière', 'ADH'),
        ('Pharmacie', 'PHARM'),
        ('Ressources Humaines', 'RH'),
        ('Qualité & Accréditation', 'QA'),
    ],
}

SERVICES_TEMPLATE = {
    'Finance & Comptabilité': ['Comptabilité Générale', 'Trésorerie', 'Contrôle de Gestion'],
    'Audit & Contrôle': ['Audit Interne', 'Contrôle Interne'],
    'Ressources Humaines': ['Recrutement', 'Formation & Développement', 'Paie & Administration'],
    'Informatique': ['Support & Helpdesk', 'Développement', 'Réseau & Sécurité'],
    'Juridique & Conformité': ['Droit des Affaires', 'Conformité & RGPD'],
    'Développement Logiciel': ['Backend', 'Frontend', 'Mobile', 'QA & Tests'],
    'Infrastructure & Cloud': ['DevOps', 'Cloud AWS/GCP', 'Monitoring'],
    'Cybersécurité': ['SOC', 'Pentest & Audit', 'Formation Sécurité'],
    'Product Management': ['Product Design', 'Product Strategy'],
    'Production & Fabrication': ['Ligne de Production A', 'Ligne de Production B', 'Atelier Assemblage'],
    'Qualité & Contrôle': ['Contrôle Qualité', 'Métrologie', 'Certifications'],
    'Maintenance': ['Maintenance Préventive', 'Maintenance Corrective'],
    'Logistique & Supply Chain': ['Approvisionnement', 'Entrepôt & Stock', 'Transport'],
    'Ingénierie de Formation': ['Conception Pédagogique', 'E-Learning', 'Évaluation'],
    'Développement RH': ['GPEC', 'Mobilité Interne', 'Bien-être au Travail'],
    'Recrutement & Talents': ['Sourcing', 'Assessment Center'],
    'Paie & Administration': ['Paie', 'Administration du Personnel'],
    'Digital Learning': ['Plateforme LMS', 'Contenus Numériques', 'Tutorat'],
    'Soins Médicaux': ['Médecine Générale', 'Spécialités', 'Urgences'],
    'Administration Hospitalière': ['Accueil & Admissions', 'Facturation'],
    'Pharmacie': ['Dispensation', 'Gestion des Stocks'],
    'Qualité & Accréditation': ['Gestion des Risques', 'Certifications ISO'],
    'Direction Générale': ['Stratégie & Développement', 'Communication'],
}

FIRST_NAMES_M = [
    'Kouassi', 'Kofi', 'Ama', 'Yaw', 'Kwame', 'Abou', 'Ibrahima', 'Seydou',
    'Mamadou', 'Oumar', 'Cheikh', 'Aliou', 'Lamine', 'Pape', 'Moussa', 'Boubacar',
    'Amadou', 'Abdoulaye', 'Samba', 'Modibo', 'Drissa', 'Adama', 'Siaka', 'Bakary',
    'Youssouf', 'Souleymane', 'Tidiane', 'Kabine', 'Lansana', 'Daouda',
    'Jean-Baptiste', 'Pierre', 'Henri', 'Louis', 'Marc', 'Paul', 'Olivier',
    'Christophe', 'Thierry', 'Laurent', 'Nicolas', 'François', 'Stéphane',
    'Antoine', 'Alexandre', 'Mathieu', 'Julien', 'Damien', 'Romain', 'Vincent',
]

FIRST_NAMES_F = [
    'Aïssatou', 'Fatoumata', 'Mariama', 'Kadiatou', 'Aminata', 'Ndeye', 'Rokhaya',
    'Bintou', 'Adja', 'Mame', 'Yacine', 'Coumba', 'Khady', 'Astou', 'Dienaba',
    'Adjoa', 'Ama', 'Efua', 'Abena', 'Akosua', 'Adwoa', 'Yaa', 'Esi', 'Araba',
    'Marie', 'Sophie', 'Claire', 'Julie', 'Céline', 'Isabelle', 'Nathalie',
    'Valérie', 'Anne', 'Sylvie', 'Christine', 'Monique', 'Patricia', 'Martine',
    'Hélène', 'Véronique', 'Sandrine', 'Laure', 'Aurélie', 'Camille', 'Emma',
    'Inès', 'Lucie', 'Manon', 'Pauline', 'Sarah', 'Alice',
]

LAST_NAMES = [
    'Koné', 'Diallo', 'Coulibaly', 'Traoré', 'Touré', 'Konaté', 'Sidibé', 'Bah',
    'Barry', 'Camara', 'Sylla', 'Baldé', 'Sow', 'Dieng', 'Mbaye', 'Fall',
    'Ndiaye', 'Sarr', 'Gaye', 'Thiam', 'Dème', 'Faye', 'Ndoye', 'Kane',
    'Kouyaté', 'Sissoko', 'Keïta', 'Dembélé', 'Sanogo', 'Bagayoko',
    'Dupont', 'Martin', 'Bernard', 'Dubois', 'Thomas', 'Robert', 'Richard',
    'Petit', 'Durand', 'Moreau', 'Simon', 'Laurent', 'Lefebvre', 'Michel',
    'Garcia', 'David', 'Bertrand', 'Roux', 'Vincent', 'Fournier',
    'Bamba', 'Gnagnon', 'Aka', 'Ake', 'Yao', 'Koffi', 'Aboua', 'Zadi',
]

JOB_TITLES_BY_DEPT = {
    'Direction Générale': [
        'Directeur Général', 'Directeur Général Adjoint', 'Secrétaire de Direction',
        'Chargé de Mission DG', 'Responsable Communication'
    ],
    'Finance & Comptabilité': [
        'Directeur Financier', 'Responsable Comptable', 'Comptable Principal',
        'Comptable', 'Contrôleur de Gestion', 'Trésorier', 'Analyste Financier',
        'Assistant Comptable', 'Chargé de Recouvrement'
    ],
    'Audit & Contrôle': [
        'Directeur Audit', 'Auditeur Senior', 'Auditeur', 'Contrôleur Interne',
        'Responsable Conformité', 'Analyste Risques'
    ],
    'Ressources Humaines': [
        'Directeur RH', 'Responsable RH', 'Chargé de Recrutement',
        'Gestionnaire de Paie', 'Chargé de Formation', 'Assistant RH',
        'HRBP', 'Responsable Talent Acquisition'
    ],
    'Informatique': [
        'Directeur IT', 'Responsable Systèmes', 'Développeur Senior',
        'Développeur', 'Administrateur Réseau', 'Technicien Support',
        'Chef de Projet IT', 'Analyste Business'
    ],
    'Juridique & Conformité': [
        'Directeur Juridique', 'Juriste Senior', 'Juriste', 'Responsable Conformité',
        'Paralégal', 'DPO'
    ],
    'Développement Logiciel': [
        'CTO', 'Lead Developer', 'Développeur Backend Senior', 'Développeur Frontend Senior',
        'Développeur Fullstack', 'Développeur Mobile', 'Architecte Logiciel',
        'Développeur Junior', 'Tech Lead'
    ],
    'Infrastructure & Cloud': [
        'Directeur Infrastructure', 'Ingénieur DevOps Senior', 'Ingénieur DevOps',
        'Administrateur Cloud', 'Ingénieur Réseau', 'SRE Engineer'
    ],
    'Cybersécurité': [
        'CISO', 'Analyste SOC Senior', 'Analyste SOC', 'Pentesteur',
        'Responsable Sécurité', 'Ingénieur Sécurité'
    ],
    'Product Management': [
        'CPO', 'Product Manager Senior', 'Product Manager', 'Product Owner',
        'UX Designer', 'Product Designer'
    ],
    'Production & Fabrication': [
        'Directeur de Production', 'Responsable Atelier', 'Chef d\'Équipe',
        'Opérateur de Production Senior', 'Opérateur de Production', 'Technicien'
    ],
    'Qualité & Contrôle': [
        'Directeur Qualité', 'Responsable Qualité', 'Ingénieur Qualité',
        'Technicien Contrôle Qualité', 'Auditeur Qualité'
    ],
    'Maintenance': [
        'Responsable Maintenance', 'Technicien Maintenance Senior',
        'Technicien Maintenance', 'Électromécanicien'
    ],
    'Logistique & Supply Chain': [
        'Directeur Supply Chain', 'Responsable Logistique', 'Gestionnaire Stocks',
        'Coordinateur Logistique', 'Chauffeur-Livreur', 'Agent Logistique'
    ],
    'Ingénierie de Formation': [
        'Directeur Pédagogique', 'Ingénieur Pédagogique Senior', 'Ingénieur Pédagogique',
        'Concepteur E-Learning', 'Formateur Senior', 'Formateur'
    ],
    'Développement RH': [
        'Directeur Développement RH', 'Responsable GPEC', 'Chargé de Développement RH',
        'Consultant Emploi', 'Coach RH'
    ],
    'Recrutement & Talents': [
        'Directeur Recrutement', 'Talent Acquisition Manager', 'Recruteur Senior',
        'Recruteur', 'Chasseur de Têtes', 'Responsable Marque Employeur'
    ],
    'Paie & Administration': [
        'Responsable Paie', 'Gestionnaire Paie Senior', 'Gestionnaire Paie',
        'Assistant Administration', 'Technicien Paie'
    ],
    'Digital Learning': [
        'Responsable Digital Learning', 'Expert LMS', 'Intégrateur E-Learning',
        'Chargé de Tutorat', 'Animateur Pédagogique'
    ],
    'Soins Médicaux': [
        'Médecin Chef', 'Médecin Généraliste', 'Médecin Spécialiste',
        'Infirmier(ière) Chef', 'Infirmier(ière)', 'Aide-Soignant(e)'
    ],
    'Administration Hospitalière': [
        'Directeur Administratif', 'Responsable Admissions', 'Agent d\'Accueil',
        'Responsable Facturation', 'Caissier(ière)'
    ],
    'Pharmacie': [
        'Pharmacien Chef', 'Pharmacien', 'Préparateur en Pharmacie',
        'Aide Préparateur'
    ],
    'Qualité & Accréditation': [
        'Responsable Qualité', 'Chargé de Gestion des Risques',
        'Technicien Qualité', 'Coordinateur Accréditation'
    ],
}

SKILLS_CATALOG = {
    'Techniques': [
        'Python', 'JavaScript', 'React', 'Node.js', 'SQL', 'Excel Avancé',
        'Power BI', 'Tableau', 'SAP', 'Salesforce', 'Cybersécurité',
        'Cloud Computing', 'Machine Learning', 'DevOps', 'Gestion de Projet',
        'Comptabilité', 'Audit Financier', 'Analyse Financière', 'Contrôle de Gestion',
        'Production Industrielle', 'Maintenance Préventive', 'Qualité ISO',
        'Supply Chain', 'Soins Infirmiers', 'Pharmacologie',
    ],
    'Management': [
        'Leadership', 'Management d\'Équipe', 'Coaching', 'Prise de Décision',
        'Gestion du Changement', 'Intelligence Émotionnelle', 'Négociation',
        'Gestion des Conflits', 'Planification Stratégique', 'Conduite de Réunion',
    ],
    'Transversales': [
        'Communication Orale', 'Communication Écrite', 'Travail en Équipe',
        'Gestion du Temps', 'Résolution de Problèmes', 'Créativité',
        'Adaptabilité', 'Anglais Professionnel', 'Français des Affaires',
        'Présentation PowerPoint',
    ],
    'RH': [
        'Recrutement', 'Formation & Développement', 'Gestion des Talents',
        'GPEC', 'Droit du Travail', 'Paie', 'Évaluation des Performances',
        'Marque Employeur', 'Onboarding', 'Gestion des Carrières',
    ],
}

# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = 'Seed enterprise hierarchy: 1 parent + 5 subsidiaries with 100+ employees each'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete seeded data before re-creating')

    def handle(self, *args, **options):
        if options['reset']:
            self._reset()

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== SEED ENTERPRISE ===\n'))

        with transaction.atomic():
            plan = self._get_or_create_plan()
            parent = self._create_parent(plan)
            subsidiaries = self._create_subsidiaries(parent, plan)
            skills = self._seed_global_skills(parent, subsidiaries)
            courses = self._get_existing_courses()

            for sub_data, sub_company in zip(SUBSIDIARIES, subsidiaries):
                self.stdout.write(f'\n>> Seeding subsidiary: {sub_company.name}')
                depts, services, teams = self._seed_org_structure(sub_company, sub_data['focus'])
                users = self._seed_users(sub_company, sub_data, depts, services, teams)
                self._seed_enrollments_and_progress(sub_company, users, courses)
                self._seed_sessions(sub_company, users, courses)
                self._seed_hr_data(sub_company, users, skills, courses)
                self._compute_auto_evaluations(sub_company, users, courses)
                self._seed_gamification(sub_company, users)

            self._seed_parent_admin(parent)
            self._seed_learning_paths_for_all(subsidiaries, courses)

        self.stdout.write(self.style.SUCCESS('\nEnterprise seed complete!\n'))

    # -----------------------------------------------------------------------
    # Reset
    # -----------------------------------------------------------------------

    def _reset(self):
        from apps.tenants.models import Company
        self.stdout.write(self.style.WARNING('Resetting enterprise seed data...'))
        Company.objects.filter(name__startswith='Nexus').delete()
        self.stdout.write('  Done.')

    # -----------------------------------------------------------------------
    # Plan
    # -----------------------------------------------------------------------

    def _get_or_create_plan(self):
        from apps.tenants.models import SubscriptionPlan
        plan, _ = SubscriptionPlan.objects.get_or_create(
            code='enterprise-nexus',
            defaults={
                'name': 'Enterprise Groupe',
                'plan_type': SubscriptionPlan.PLAN_TYPE_ENTERPRISE,
                'price': Decimal('500000'),
                'currency': 'XOF',
                'billing_cycle': SubscriptionPlan.BILLING_YEARLY,
                'max_users': 5000,
                'max_storage_gb': 500,
                'features': {
                    'multi_entity': True,
                    'advanced_analytics': True,
                    'custom_branding': True,
                    'api_access': True,
                    'sso': True,
                    'dedicated_support': True,
                },
            },
        )
        return plan

    # -----------------------------------------------------------------------
    # Companies
    # -----------------------------------------------------------------------

    def _create_parent(self, plan):
        from apps.tenants.models import Company
        parent, created = Company.objects.get_or_create(
            name=PARENT_COMPANY['name'],
            defaults={
                **{k: v for k, v in PARENT_COMPANY.items() if k != 'name'},
                'plan': plan,
                'subscription_status': Company.STATUS_ACTIVE,
                'subscription_start': _date_past(365),
                'subscription_end': _date_future(365),
                'is_active': True,
            },
        )
        status = 'created' if created else 'exists'
        self.stdout.write(f'  Parent company [{status}]: {parent.name}')
        return parent

    def _create_subsidiaries(self, parent, plan):
        from apps.tenants.models import Company
        result = []
        for data in SUBSIDIARIES:
            sub, created = Company.objects.get_or_create(
                name=data['name'],
                defaults={
                    'legal_name': data['legal_name'],
                    'sector': data['sector'],
                    'country': data['country'],
                    'address': data['address'],
                    'phone': data['phone'],
                    'email': data['email'],
                    'website': data['website'],
                    'parent': parent,
                    'plan': plan,
                    'subscription_status': Company.STATUS_ACTIVE,
                    'subscription_start': _date_past(300),
                    'subscription_end': _date_future(365),
                    'is_active': True,
                },
            )
            status = 'created' if created else 'exists'
            self.stdout.write(f'  Subsidiary [{status}]: {sub.name}')
            result.append(sub)
        return result

    # -----------------------------------------------------------------------
    # Skills (global + per company)
    # -----------------------------------------------------------------------

    def _seed_global_skills(self, parent, subsidiaries):
        from apps.hr_analytics.models import Skill
        all_companies = [parent] + subsidiaries
        skills = []
        for cat, names in SKILLS_CATALOG.items():
            for name in names:
                for company in all_companies:
                    skill, _ = Skill.objects.get_or_create(
                        company=company, name=name,
                        defaults={'category': cat},
                    )
                    if company == subsidiaries[0]:  # avoid dupes, collect from first sub
                        skills.append((name, cat))
        # Return flat list of skill names for later use
        return [name for cat, names in SKILLS_CATALOG.items() for name in names]

    # -----------------------------------------------------------------------
    # Org structure
    # -----------------------------------------------------------------------

    def _seed_org_structure(self, company, focus):
        from apps.tenants.models import Department, Service, Team

        dept_defs = DEPARTMENTS_BY_FOCUS.get(focus, DEPARTMENTS_BY_FOCUS['finance'])
        departments = []
        for dept_name, dept_code in dept_defs:
            dept, _ = Department.objects.get_or_create(
                company=company, name=dept_name,
                defaults={'code': dept_code},
            )
            departments.append(dept)

        services = []
        for dept in departments:
            svc_names = SERVICES_TEMPLATE.get(dept.name, ['Service Général'])
            for svc_name in svc_names:
                svc, _ = Service.objects.get_or_create(
                    company=company, department=dept, name=svc_name,
                )
                services.append(svc)

        teams = []
        for i, svc in enumerate(services[:12]):  # cap at 12 teams per company
            team, _ = Team.objects.get_or_create(
                company=company, name=f'Équipe {svc.name[:40]}',
                defaults={'service': svc},
            )
            teams.append(team)

        return departments, services, teams

    # -----------------------------------------------------------------------
    # Users (100+ per subsidiary)
    # -----------------------------------------------------------------------

    def _seed_users(self, company, sub_data, departments, services, teams):
        from apps.accounts.models import User
        from apps.core.constants import Roles

        slug = sub_data['slug_prefix']
        focus = sub_data['focus']
        created_users = []

        # 1 company admin
        admin = self._create_user(
            company, f'admin.{slug}@nexus.ci', 'Admin', company.name.split()[1] if len(company.name.split()) > 1 else 'Admin',
            Roles.COMPANY_ADMIN, departments[0], None, None,
            job_title='Directeur Général', hire_date=_date_past(730), employee_id=f'{slug.upper()}-001',
        )
        created_users.append(admin)

        # 2-3 HR
        hr_dept = next((d for d in departments if 'Ressources Humaines' in d.name), departments[1])
        for i in range(3):
            gender = random.choice(['M', 'F'])
            fn = random.choice(FIRST_NAMES_F if gender == 'F' else FIRST_NAMES_M)
            ln = random.choice(LAST_NAMES)
            u = self._create_user(
                company, f'rh{i+1}.{slug}@nexus.ci', fn, ln,
                Roles.HR, hr_dept, None, None,
                job_title=random.choice(['Responsable RH', 'Chargé de Formation', 'Gestionnaire de Paie']),
                hire_date=_date_past(random.randint(180, 900)),
                employee_id=f'{slug.upper()}-HR{i+1:02d}',
            )
            created_users.append(u)

        # 4-5 trainers
        for i in range(4):
            gender = random.choice(['M', 'F'])
            fn = random.choice(FIRST_NAMES_F if gender == 'F' else FIRST_NAMES_M)
            ln = random.choice(LAST_NAMES)
            u = self._create_user(
                company, f'formateur{i+1}.{slug}@nexus.ci', fn, ln,
                Roles.TRAINER, random.choice(departments), None, None,
                job_title='Formateur',
                hire_date=_date_past(random.randint(180, 700)),
                employee_id=f'{slug.upper()}-TR{i+1:02d}',
                is_trainer_approved=True,
            )
            created_users.append(u)

        # 8-10 managers
        manager_users = []
        for i in range(8):
            dept = departments[i % len(departments)]
            svc = next((s for s in services if s.department_id == dept.id), None)
            gender = random.choice(['M', 'F'])
            fn = random.choice(FIRST_NAMES_F if gender == 'F' else FIRST_NAMES_M)
            ln = random.choice(LAST_NAMES)
            u = self._create_user(
                company, f'manager{i+1}.{slug}@nexus.ci', fn, ln,
                Roles.MANAGER, dept, svc, None,
                job_title=random.choice(JOB_TITLES_BY_DEPT.get(dept.name, ['Responsable'])),
                hire_date=_date_past(random.randint(200, 1000)),
                employee_id=f'{slug.upper()}-MG{i+1:02d}',
            )
            created_users.append(u)
            manager_users.append(u)

        # 85+ employees
        emp_count = 0
        depts_cycle = departments * 20  # cycle through departments
        for i in range(90):
            dept = depts_cycle[i % len(departments)]
            svc_options = [s for s in services if s.department_id == dept.id]
            svc = random.choice(svc_options) if svc_options else None
            team = random.choice(teams) if teams else None
            manager = random.choice(manager_users) if manager_users else None
            gender = random.choice(['M', 'F'])
            fn = random.choice(FIRST_NAMES_F if gender == 'F' else FIRST_NAMES_M)
            ln = random.choice(LAST_NAMES)
            titles = JOB_TITLES_BY_DEPT.get(dept.name, ['Collaborateur', 'Assistant', 'Chargé de Mission'])
            u = self._create_user(
                company, f'emp{i+1:03d}.{slug}@nexus.ci', fn, ln,
                Roles.EMPLOYEE, dept, svc, team,
                job_title=random.choice(titles),
                hire_date=_date_past(random.randint(30, 1500)),
                employee_id=f'{slug.upper()}-EMP{i+1:03d}',
                manager=manager,
                country=random.choice(['Côte d\'Ivoire', 'Sénégal', 'Mali', 'Guinée', 'Burkina Faso', 'Cameroun', 'France']),
            )
            created_users.append(u)
            emp_count += 1

        self.stdout.write(f'    Users: {len(created_users)} (admin+hr+trainer+manager+employee)')
        return created_users

    def _create_user(self, company, email, first_name, last_name, role, dept, service, team,
                     job_title='', hire_date=None, employee_id='', manager=None,
                     country='Côte d\'Ivoire', is_trainer_approved=False):
        from apps.accounts.models import User

        if User.objects.filter(email=email).exists():
            return User.objects.get(email=email)

        phones = [f'+225 07 {random.randint(10,99)} {random.randint(10,99)} {random.randint(10,99)} {random.randint(10,99)}']

        user = User.objects.create(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=make_password('nexus2026!'),
            role=role,
            company=company,
            department=dept,
            service=service,
            team=team,
            manager=manager,
            phone=phones[0],
            job_title=job_title,
            hire_date=hire_date,
            birth_date=_date_past(random.randint(8000, 16000)),
            country=country,
            employee_id=employee_id,
            is_trainer_approved=is_trainer_approved,
            is_active=True,
            is_staff=False,
            last_active_at=_past(random.randint(0, 30)),
            bio=f'{first_name} {last_name} est {job_title} chez {company.name}.',
        )
        return user

    # -----------------------------------------------------------------------
    # Enrollments & lesson progress
    # -----------------------------------------------------------------------

    def _get_existing_courses(self):
        from apps.courses.models import Course
        courses = list(Course.objects.filter(status='published').prefetch_related(
            'sections__chapters__lessons'
        ))
        if not courses:
            self.stdout.write(self.style.WARNING('  No published courses found. Run seed_all first.'))
        return courses

    def _seed_enrollments_and_progress(self, company, users, courses):
        from apps.courses.models import Enrollment
        from apps.progression.models import LessonProgress

        if not courses:
            return

        employees = [u for u in users if hasattr(u, 'role')]
        enrolled_count = 0
        progress_count = 0

        for user in employees:
            # Each user enrolls in 2-4 courses
            user_courses = random.sample(courses, min(random.randint(2, 4), len(courses)))
            for course in user_courses:
                enrollment, _ = Enrollment.objects.get_or_create(
                    user=user,
                    course=course,
                    defaults={
                        'source': Enrollment.SOURCE_ASSIGNED,
                        'enrolled_at': _past(random.randint(10, 200)),
                    },
                )
                enrolled_count += 1

                # Get all lessons for this course
                all_lessons = []
                for section in course.sections.all():
                    for chapter in section.chapters.all():
                        all_lessons.extend(list(chapter.lessons.all()))

                if not all_lessons:
                    continue

                # Decide completion profile: 20% fully done, 50% in progress, 30% just started
                r = random.random()
                if r < 0.20:
                    completed_lessons = all_lessons  # 100%
                elif r < 0.70:
                    n = max(1, int(len(all_lessons) * random.uniform(0.2, 0.85)))
                    completed_lessons = all_lessons[:n]
                else:
                    completed_lessons = all_lessons[:1]

                for lesson in all_lessons:
                    is_done = lesson in completed_lessons
                    watch_pct = Decimal(str(round(random.uniform(85, 100), 2))) if is_done else Decimal(str(round(random.uniform(0, 70), 2)))
                    prog, created = LessonProgress.objects.get_or_create(
                        user=user,
                        lesson=lesson,
                        defaults={
                            'is_completed': is_done,
                            'watch_percent': watch_pct,
                            'watched_seconds': int(watch_pct * 3),
                            'time_spent_seconds': random.randint(120, 1800),
                            'completed_at': _past(random.randint(1, 60)) if is_done else None,
                        },
                    )
                    if created:
                        progress_count += 1

                # Update enrollment progress
                if all_lessons:
                    done = sum(1 for l in all_lessons if LessonProgress.objects.filter(user=user, lesson=l, is_completed=True).exists())
                    pct = Decimal(str(round(done / len(all_lessons) * 100, 2)))
                    enrollment.progress_percent = pct
                    if pct >= 100:
                        enrollment.status = Enrollment.STATUS_COMPLETED
                        if not enrollment.completed_at:
                            enrollment.completed_at = _past(random.randint(1, 30))
                    elif pct > 0:
                        enrollment.status = Enrollment.STATUS_IN_PROGRESS
                    enrollment.save(update_fields=['progress_percent', 'status', 'completed_at'])

        self.stdout.write(f'    Enrollments: {enrolled_count} | LessonProgress: {progress_count}')

    # -----------------------------------------------------------------------
    # Assessment attempts
    # -----------------------------------------------------------------------

    def _seed_sessions(self, company, users, courses):
        from apps.learning_paths.models import TrainingSession, SessionParticipant
        from apps.assessments.models import Assessment, AssessmentAttempt

        trainer_users = [u for u in users if u.role == 'trainer']
        if not trainer_users:
            trainer_users = users[:2]

        session_count = 0
        attempt_count = 0

        # Create 6 training sessions per company
        session_titles = [
            'Formation Management & Leadership', 'Excel & Power BI Avancé',
            'Communication Professionnelle', 'Cybersécurité en Entreprise',
            'Gestion de Projet Agile', 'Bien-être & Qualité de Vie au Travail',
        ]

        sessions_created = []
        for i, title in enumerate(session_titles):
            course = courses[i % len(courses)] if courses else None
            trainer = random.choice(trainer_users)
            is_online = i % 2 == 0
            delta_days = random.randint(-60, 90)
            start = _now() + timedelta(days=delta_days)
            end = start + timedelta(hours=random.randint(2, 8))
            session, _ = TrainingSession.objects.get_or_create(
                company=company,
                title=title,
                defaults={
                    'course': course,
                    'trainer': trainer,
                    'location_type': 'online' if is_online else 'onsite',
                    'address': '' if is_online else f'{company.address}',
                    'join_url': f'https://meet.nexus.ci/session-{i+1}' if is_online else '',
                    'start_datetime': start,
                    'end_datetime': end,
                    'capacity': random.randint(15, 30),
                },
            )
            sessions_created.append(session)
            session_count += 1

        # Register 15-25 employees per session with realistic attendance
        employee_users = [u for u in users if u.role == 'employee']
        for session in sessions_created:
            participants = random.sample(employee_users, min(random.randint(15, 25), len(employee_users)))
            session_in_past = session.start_datetime < _now()
            for user in participants:
                status_choices = (
                    ['attended', 'attended', 'attended', 'absent']
                    if session_in_past
                    else ['registered', 'registered', 'registered', 'cancelled']
                )
                SessionParticipant.objects.get_or_create(
                    session=session, user=user,
                    defaults={'status': random.choice(status_choices)},
                )

        # Create assessment attempts for enrolled users
        from apps.courses.models import Course
        from apps.assessments.models import Assessment, AssessmentAttempt

        for course in courses[:3]:
            assessments = list(Assessment.objects.filter(course=course))
            if not assessments:
                continue
            enrolled_users = [u for u in users
                              if u.lesson_progresses.filter(lesson__chapter__section__course=course).exists()]
            for user in enrolled_users[:40]:  # cap to keep seeding fast
                for assessment in assessments[:2]:
                    if AssessmentAttempt.objects.filter(assessment=assessment, user=user).exists():
                        continue
                    score = Decimal(str(round(random.uniform(45, 98), 2)))
                    passed = score >= assessment.passing_score
                    attempt = AssessmentAttempt.objects.create(
                        assessment=assessment,
                        user=user,
                        attempt_number=1,
                        submitted_at=_past(random.randint(1, 90)),
                        score=score,
                        is_passed=passed,
                        status=AssessmentAttempt.STATUS_GRADED,
                    )
                    attempt_count += 1

        self.stdout.write(f'    Sessions: {session_count} | Assessment attempts: {attempt_count}')

    # -----------------------------------------------------------------------
    # HR data (skills, PDI, 360°, budget)
    # -----------------------------------------------------------------------

    def _seed_hr_data(self, company, users, skill_names, courses):
        from apps.hr_analytics.models import (
            Skill, EmployeeSkill, JobRole, JobRoleSkillRequirement,
            IndividualDevelopmentPlan, PDIObjective,
            TrainingBudgetEntry,
        )

        company_skills = list(Skill.objects.filter(company=company))
        if not company_skills:
            return

        # Job roles per company
        job_role_titles = [
            'Analyste Senior', 'Chef de Projet', 'Responsable Département',
            'Coordinateur', 'Spécialiste Technique', 'Consultant',
        ]
        job_roles = []
        for title in job_role_titles:
            jr, _ = JobRole.objects.get_or_create(company=company, title=title)
            job_roles.append(jr)
            # Assign 3 skill requirements
            for skill in random.sample(company_skills, min(3, len(company_skills))):
                JobRoleSkillRequirement.objects.get_or_create(
                    job_role=jr, skill=skill,
                    defaults={'required_level': random.randint(2, 4)},
                )

        # Employee skills (3-7 skills per person)
        skill_count = 0
        for user in users:
            n_skills = random.randint(3, 7)
            chosen = random.sample(company_skills, min(n_skills, len(company_skills)))
            for skill in chosen:
                EmployeeSkill.objects.get_or_create(
                    user=user, skill=skill,
                    defaults={
                        'level': random.randint(1, 4),
                        'source': EmployeeSkill.SOURCE_MANAGER,
                    },
                )
                skill_count += 1

        # PDI for 40% of users
        pdi_users = random.sample(users, max(1, int(len(users) * 0.4)))
        hr_users = [u for u in users if u.role == 'hr'] or [users[0]]
        pdi_count = 0
        for user in pdi_users:
            creator = random.choice(hr_users)
            plan, created = IndividualDevelopmentPlan.objects.get_or_create(
                user=user,
                period_start=_date_past(180),
                defaults={
                    'created_by': creator,
                    'period_end': _date_future(180),
                    'status': random.choice(['active', 'active', 'completed', 'draft']),
                },
            )
            if created:
                pdi_count += 1
                # Add 2-3 objectives
                for _ in range(random.randint(2, 3)):
                    skill = random.choice(company_skills) if company_skills else None
                    course = random.choice(courses) if courses else None
                    PDIObjective.objects.create(
                        plan=plan,
                        skill=skill,
                        course=course,
                        description=f'Développer la compétence en {skill.name if skill else "domaine métier"}',
                        target_date=_date_future(random.randint(30, 180)),
                        expected_result='Atteindre le niveau 3/5 sur cette compétence',
                        status=random.choice(['not_started', 'in_progress', 'achieved']),
                    )

        # Training budget
        for year in [2024, 2025, 2026]:
            budget = Decimal(str(random.randint(5_000_000, 50_000_000)))
            spent = Decimal(str(random.randint(1_000_000, int(float(budget) * 0.8))))
            TrainingBudgetEntry.objects.get_or_create(
                company=company, year=year,
                defaults={
                    'amount_allocated': budget,
                    'amount_spent': spent,
                    'notes': f'Budget formation {year} — comprend les formations externes et internes.',
                },
            )

        self.stdout.write(f'    EmployeeSkills: {skill_count} | PDI plans: {pdi_count}')

    # -----------------------------------------------------------------------
    # Auto-evaluation
    # -----------------------------------------------------------------------

    def _compute_auto_evaluations(self, company, users, courses):
        from apps.hr_analytics.models import (
            Skill, EmployeeSkill, Evaluation360Campaign, Evaluation360Response,
        )
        from apps.progression.models import LessonProgress
        from apps.assessments.models import AssessmentAttempt
        from apps.learning_paths.models import SessionParticipant
        from apps.gamification.models import XPLog, UserStreak

        company_skills = list(Skill.objects.filter(company=company))
        hr_users = [u for u in users if u.role in ('hr', 'company_admin')] or [users[0]]
        manager_users = [u for u in users if u.role == 'manager'] or [users[0]]

        campaign_count = 0
        response_count = 0
        skill_auto_count = 0

        for user in users:
            # ------ Compute metrics ------
            # 1. Completion rate
            total_lessons = LessonProgress.objects.filter(user=user).count()
            done_lessons = LessonProgress.objects.filter(user=user, is_completed=True).count()
            completion_rate = (done_lessons / total_lessons * 100) if total_lessons > 0 else 0

            # 2. Average assessment score
            attempts = AssessmentAttempt.objects.filter(
                user=user, status=AssessmentAttempt.STATUS_GRADED
            )
            avg_score = float(sum(float(a.score or 0) for a in attempts) / len(attempts)) if attempts else 0

            # 3. Attendance rate
            total_sessions = SessionParticipant.objects.filter(user=user).exclude(
                status=SessionParticipant.STATUS_CANCELLED
            ).count()
            attended = SessionParticipant.objects.filter(
                user=user, status=SessionParticipant.STATUS_ATTENDED
            ).count()
            attendance_rate = (attended / total_sessions * 100) if total_sessions > 0 else 50  # default 50

            # 4. XP total
            xp_total = sum(x.amount for x in XPLog.objects.filter(user=user))

            # 5. Streak
            try:
                streak = user.streak.current_streak
            except Exception:
                streak = 0

            # ------ Compute overall score ------
            # Weighted: completion 40%, score 35%, attendance 15%, xp+streak 10%
            xp_score = min(100, xp_total / 10)  # 1000 XP = 100 score
            streak_score = min(100, streak * 5)  # 20 days = 100 score
            assiduity_score = (xp_score * 0.5 + streak_score * 0.5)

            overall = (
                completion_rate * 0.40 +
                avg_score * 0.35 +
                attendance_rate * 0.15 +
                assiduity_score * 0.10
            )
            overall = round(min(100, max(0, overall)), 2)

            # ------ Update EmployeeSkill levels based on completion ------
            for emp_skill in EmployeeSkill.objects.filter(user=user):
                # Adjust level: if high completion → boost, if low → keep or reduce
                current = emp_skill.level
                boost = 0
                if completion_rate >= 80 and avg_score >= 75:
                    boost = 1
                elif completion_rate < 30 or avg_score < 50:
                    boost = -1
                new_level = max(0, min(5, current + boost))
                if new_level != current:
                    EmployeeSkill.objects.filter(pk=emp_skill.pk).update(
                        level=new_level, source=EmployeeSkill.SOURCE_AUTO
                    )
                    skill_auto_count += 1

            # ------ Create 360° campaign for 30% of employees ------
            if user.role == 'employee' and random.random() < 0.30:
                hr = random.choice(hr_users)
                campaign, created = Evaluation360Campaign.objects.get_or_create(
                    company=company,
                    target_user=user,
                    title=f'Évaluation 360° – {user.get_full_name()} – 2026',
                    defaults={
                        'period_start': _date_past(60),
                        'period_end': _date_past(1),
                        'status': Evaluation360Campaign.STATUS_CLOSED,
                        'created_by': hr,
                    },
                )
                if created:
                    campaign_count += 1
                    # Self evaluation
                    Evaluation360Response.objects.get_or_create(
                        campaign=campaign, evaluator=user,
                        evaluator_type=Evaluation360Response.EVALUATOR_SELF,
                        defaults={
                            'answers': self._build_eval_answers(overall * 0.9),
                            'overall_score': Decimal(str(round(overall * 0.9, 2))),
                            'submitted_at': _past(2),
                        },
                    )
                    response_count += 1

                    # Manager evaluation
                    mgr = user.manager or (random.choice(manager_users) if manager_users else None)
                    if mgr:
                        Evaluation360Response.objects.get_or_create(
                            campaign=campaign, evaluator=mgr,
                            evaluator_type=Evaluation360Response.EVALUATOR_MANAGER,
                            defaults={
                                'answers': self._build_eval_answers(overall),
                                'overall_score': Decimal(str(round(overall, 2))),
                                'submitted_at': _past(1),
                            },
                        )
                        response_count += 1

                    # HR final evaluation (computed from all)
                    Evaluation360Response.objects.get_or_create(
                        campaign=campaign, evaluator=hr,
                        evaluator_type=Evaluation360Response.EVALUATOR_FINAL,
                        defaults={
                            'answers': self._build_eval_answers(overall),
                            'overall_score': Decimal(str(overall)),
                            'submitted_at': _past(0),
                        },
                    )
                    response_count += 1

        self.stdout.write(
            f'    Auto-evals: {campaign_count} campaigns | {response_count} responses | {skill_auto_count} skill updates'
        )

    def _build_eval_answers(self, base_score):
        """Generate realistic answer structure for Evaluation360Response.answers."""
        score = max(0, min(100, base_score))
        return {
            'competences_metier': round(score * random.uniform(0.85, 1.10), 1),
            'qualite_travail': round(score * random.uniform(0.90, 1.05), 1),
            'cooperation': round(score * random.uniform(0.80, 1.15), 1),
            'initiative': round(score * random.uniform(0.75, 1.10), 1),
            'communication': round(score * random.uniform(0.85, 1.05), 1),
            'respect_delais': round(score * random.uniform(0.80, 1.10), 1),
            'overall_comment': f'Performance globale évaluée à {round(score, 1)}/100.',
        }

    # -----------------------------------------------------------------------
    # Gamification
    # -----------------------------------------------------------------------

    def _seed_gamification(self, company, users):
        from apps.gamification.models import Badge, UserBadge, XPLog, UserStreak, Level, Challenge, ChallengeParticipation

        # Ensure levels exist
        levels_data = [
            ('Débutant', 0, 'Star'), ('Bronze', 500, 'Award'), ('Argent', 1500, 'Trophy'),
            ('Or', 3000, 'Medal'), ('Platine', 6000, 'Crown'), ('Diamant', 10000, 'Diamond'),
        ]
        for name, min_xp, icon in levels_data:
            Level.objects.get_or_create(name=name, defaults={'min_xp': min_xp, 'icon': icon})

        # Badges per company
        badges_data = [
            ('Première Formation', 'Cours inaugural complété', Badge.CRITERIA_COURSE_COMPLETION),
            ('Apprenant Assidu', '7 jours consécutifs de connexion', Badge.CRITERIA_STREAK),
            ('Expert 360°', 'Évaluation globale > 85/100', Badge.CRITERIA_CUSTOM),
            ('Superstar XP', 'Plus de 2000 XP cumulés', Badge.CRITERIA_XP_THRESHOLD),
            ('Formateur du Mois', 'Session animée avec excellence', Badge.CRITERIA_CUSTOM),
        ]
        company_badges = []
        for title, desc, ctype in badges_data:
            badge, _ = Badge.objects.get_or_create(
                company=company, title=title,
                defaults={'description': desc, 'criteria_type': ctype, 'criteria_value': {}},
            )
            company_badges.append(badge)

        # XP and streaks for each user
        xp_total_count = 0
        for user in users:
            existing_xp = XPLog.objects.filter(user=user).aggregate(
                total=__import__('django.db.models', fromlist=['Sum']).Sum('amount')
            )['total'] or 0

            if existing_xp == 0:
                xp_reasons = [
                    (50, 'Connexion quotidienne'), (100, 'Leçon terminée'),
                    (200, 'Quiz réussi'), (150, 'Cours complété'),
                    (75, 'Forum — réponse utile'), (300, 'Session de formation'),
                ]
                for _ in range(random.randint(3, 12)):
                    reason_xp, reason_label = random.choice(xp_reasons)
                    XPLog.objects.create(
                        user=user,
                        amount=reason_xp,
                        reason=reason_label,
                        source_type='seed',
                    )
                    xp_total_count += 1

            # Streak
            UserStreak.objects.get_or_create(
                user=user,
                defaults={
                    'current_streak': random.randint(0, 30),
                    'longest_streak': random.randint(5, 60),
                    'last_active_date': _date_past(random.randint(0, 5)),
                },
            )

            # Award badges probabilistically
            if company_badges:
                for badge in random.sample(company_badges, random.randint(0, min(3, len(company_badges)))):
                    UserBadge.objects.get_or_create(user=user, badge=badge)

        # Challenges
        challenge_titles = [
            'Challenge Octobre — 5 cours en 1 mois',
            'Marathon Formation Q1 2026',
            'Défi Compétences Numériques',
        ]
        for title in challenge_titles:
            badge_reward = random.choice(company_badges) if company_badges else None
            challenge, _ = Challenge.objects.get_or_create(
                company=company, title=title,
                defaults={
                    'description': f'{title} : relevez le défi et gagnez des points XP !',
                    'start_date': _date_past(30),
                    'end_date': _date_future(30),
                    'xp_reward': random.randint(200, 500),
                    'badge_reward': badge_reward,
                    'criteria': {'type': 'course_completions', 'count': random.randint(2, 5)},
                },
            )
            # Register 20-40% of users
            participants = random.sample(users, max(1, int(len(users) * random.uniform(0.2, 0.4))))
            for user in participants:
                ChallengeParticipation.objects.get_or_create(
                    challenge=challenge, user=user,
                    defaults={
                        'status': random.choice([
                            ChallengeParticipation.STATUS_JOINED,
                            ChallengeParticipation.STATUS_JOINED,
                            ChallengeParticipation.STATUS_COMPLETED,
                        ]),
                    },
                )

        self.stdout.write(f'    XP logs: {xp_total_count} | Badges: {len(company_badges)} | Challenges: {len(challenge_titles)}')

    # -----------------------------------------------------------------------
    # Parent admin
    # -----------------------------------------------------------------------

    def _seed_parent_admin(self, parent):
        from apps.accounts.models import User
        from apps.core.constants import Roles

        admin, created = User.objects.get_or_create(
            email='dg.groupe@nexus.ci',
            defaults={
                'first_name': 'Directeur',
                'last_name': 'Groupe',
                'password': make_password('nexus2026!'),
                'role': Roles.COMPANY_ADMIN,
                'company': parent,
                'job_title': 'Directeur Général du Groupe',
                'hire_date': _date_past(1200),
                'employee_id': 'NEXUS-DG-001',
                'is_active': True,
                'bio': 'Directeur Général du Groupe Nexus International.',
            },
        )
        status = 'created' if created else 'exists'
        self.stdout.write(f'\n  Parent admin [{status}]: {admin.email}')

    # -----------------------------------------------------------------------
    # Learning paths across subsidiaries
    # -----------------------------------------------------------------------

    def _seed_learning_paths_for_all(self, subsidiaries, courses):
        from apps.learning_paths.models import LearningPath, LearningPathStep, LearningPathEnrollment
        from apps.accounts.models import User

        if not courses:
            return

        path_templates = [
            {
                'title': 'Parcours Onboarding Collaborateur',
                'path_type': LearningPath.TYPE_ONBOARDING,
                'description': 'Parcours d\'intégration obligatoire pour tout nouvel employé.',
                'courses_count': min(2, len(courses)),
            },
            {
                'title': 'Parcours Manager Excellence',
                'path_type': LearningPath.TYPE_MANAGER,
                'description': 'Développement des compétences managériales.',
                'courses_count': min(2, len(courses)),
            },
            {
                'title': 'Parcours Digital & IA',
                'path_type': LearningPath.TYPE_JOB_ROLE,
                'description': 'Montée en compétences sur les outils numériques et l\'IA.',
                'courses_count': min(3, len(courses)),
            },
        ]

        path_count = 0
        for sub in subsidiaries:
            admin_user = User.objects.filter(company=sub, role='company_admin').first()
            if not admin_user:
                continue

            sub_paths = []
            for tpl in path_templates:
                path, _ = LearningPath.objects.get_or_create(
                    company=sub,
                    title=tpl['title'],
                    defaults={
                        'description': tpl['description'],
                        'path_type': tpl['path_type'],
                        'created_by': admin_user,
                        'is_active': True,
                        'certificate_enabled': True,
                    },
                )
                # Add course steps
                for order, course in enumerate(courses[:tpl['courses_count']], 1):
                    LearningPathStep.objects.get_or_create(
                        path=path, course=course,
                        defaults={'order': order, 'is_mandatory': True},
                    )
                sub_paths.append(path)
                path_count += 1

            # Enroll new employees (hired in last 90 days) in onboarding path
            onboarding_path = sub_paths[0] if sub_paths else None
            if onboarding_path:
                new_employees = User.objects.filter(
                    company=sub,
                    role='employee',
                    hire_date__gte=_date_past(90),
                )
                for emp in new_employees[:20]:
                    LearningPathEnrollment.objects.get_or_create(
                        user=emp, path=onboarding_path,
                        defaults={
                            'assigned_by': admin_user,
                            'status': LearningPathEnrollment.STATUS_IN_PROGRESS,
                        },
                    )

        self.stdout.write(f'\n  Learning paths: {path_count} across {len(subsidiaries)} subsidiaries')
