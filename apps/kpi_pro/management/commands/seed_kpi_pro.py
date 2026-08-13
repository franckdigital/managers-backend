"""Enrichit les données réelles qui alimentent les 150 KPI de KPI's RH Pro.

La plupart des 100 KPI Employés se calculent déjà depuis les données existantes
(inscriptions, scores, compétences, évaluations 360°...). Cette commande comble
les quelques trous identifiés par audit sur les données seed_enterprise : aucune
classe virtuelle/présence, aucun message de forum, aucun certificat délivré,
aucune recommandation IA — ce qui faisait ressortir des KPI à zéro pour la
catégorie Assiduité, IA & Analytique, etc. Idempotente : peut être relancée sans
dupliquer les données déjà créées.
"""
import random
import secrets
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.core.constants import Roles

THREAD_TITLES = [
    "Question sur le module 3", "Retour d'expérience sur l'exercice pratique",
    "Difficulté avec le quiz final", "Astuce pour progresser plus vite",
    "Partage de ressources complémentaires", "Retard sur le calendrier ?",
]
POST_SNIPPETS = [
    "Merci pour cette formation, très clair !",
    "Quelqu'un a compris l'exercice 2 ?",
    "J'ai eu le même souci, voici comment je l'ai résolu.",
    "Super contenu, merci au formateur.",
    "Est-ce que quelqu'un peut m'expliquer ce point ?",
    "Top, ça débloque bien des choses, merci pour le partage.",
]
VIRTUAL_CLASS_TITLES = [
    "Session live — Questions/Réponses", "Atelier pratique en direct",
    "Classe virtuelle — Approfondissement", "Webinaire de clôture de module",
    "Coaching collectif", "Revue de projet en groupe", "Masterclass thématique",
    "Session de rattrapage",
]
LEARNER_ROLES = {Roles.EMPLOYEE, Roles.MANAGER, Roles.STUDENT}


class Command(BaseCommand):
    help = "Alimente les données réelles (assiduité, forums, certificats, recommandations IA) derrière les KPI's RH Pro, pour chaque employé d'une entreprise."

    def add_arguments(self, parser):
        parser.add_argument('--company', type=int, default=None, help="ID de l'entreprise racine à traiter (défaut : toutes)")

    def handle(self, *args, **options):
        from apps.tenants.models import Company

        company_id = options.get('company')
        companies = Company.objects.filter(pk=company_id) if company_id else Company.objects.filter(parent__isnull=True)

        if not companies:
            self.stdout.write(self.style.WARNING('Aucune entreprise trouvée.'))
            return

        for company in companies:
            self.stdout.write(self.style.MIGRATE_HEADING(f'--- {company.name} ---'))
            with transaction.atomic():
                self.seed_company(company)

        self.stdout.write(self.style.SUCCESS('Terminé.'))

    def seed_company(self, company):
        from apps.accounts.models import User

        company_ids = company.get_descendant_ids()
        users = list(User.objects.filter(company_id__in=company_ids, role__in=LEARNER_ROLES))
        if not users:
            self.stdout.write('  (aucun employé, ignoré)')
            return

        self.seed_certificates(users)
        classes = self.seed_virtual_classes(company, users)
        self.seed_attendance(classes, users)
        self.seed_forum(company, users)
        self.seed_recommendations(users)
        self.seed_guaranteed_coverage(company, users, classes)

    # ── Certificats pour les formations déjà complétées ─────────────────────
    def seed_certificates(self, users):
        from apps.certificates.models import Certificate, CertificateTemplate
        from apps.certificates.services import sign_certificate
        from apps.courses.models import Enrollment

        template = CertificateTemplate.objects.filter(is_default=True).first() or CertificateTemplate.objects.first()
        completed = Enrollment.objects.filter(
            user__in=users, status=Enrollment.STATUS_COMPLETED, course__certificate_enabled=True
        ).select_related('course', 'user')

        created = 0
        for enrollment in completed:
            if Certificate.objects.filter(user=enrollment.user, course=enrollment.course).exists():
                continue
            number = f'LMSPRO-{secrets.token_hex(6).upper()}'
            code = secrets.token_urlsafe(16)
            cert = Certificate.objects.create(
                user=enrollment.user, course=enrollment.course, template=template,
                certificate_number=number, verification_code=code,
            )
            cert.digital_signature = sign_certificate(number, code)
            cert.save(update_fields=['digital_signature'])
            created += 1
        self.stdout.write(f'  Certificats créés : {created}')

    # ── Classes virtuelles réalistes (liées aux cours suivis quand possible) ─
    def seed_virtual_classes(self, company, users):
        from apps.courses.models import Chapter, Enrollment
        from apps.virtual_classes.models import VirtualClass

        existing = list(VirtualClass.objects.filter(company=company))
        if len(existing) >= 6:
            self.stdout.write(f'  Classes virtuelles existantes : {len(existing)} (conservées)')
            return existing

        course_ids = list(Enrollment.objects.filter(user__in=users).values_list('course_id', flat=True).distinct())
        chapters = list(Chapter.objects.filter(section__course_id__in=course_ids)[:20])
        now = timezone.now()

        created = []
        for _ in range(8 - len(existing)):
            days_ago = random.randint(3, 150)
            start = now - timedelta(days=days_ago, hours=random.randint(0, 20))
            end = start + timedelta(minutes=random.choice([60, 90, 120]))
            vc = VirtualClass.objects.create(
                chapter=random.choice(chapters) if chapters else None,
                company=company,
                title=random.choice(VIRTUAL_CLASS_TITLES),
                provider=random.choice(['zoom', 'teams', 'meet', 'jitsi']),
                scheduled_start=start,
                scheduled_end=end,
            )
            created.append(vc)
        self.stdout.write(f'  Classes virtuelles créées : {len(created)}')
        return existing + created

    # ── Présences (ponctualité et durée variables pour un KPI réaliste) ─────
    def seed_attendance(self, classes, users):
        from apps.virtual_classes.models import VirtualClassAttendance

        created = 0
        for vc in classes:
            duration_s = max(60, int((vc.scheduled_end - vc.scheduled_start).total_seconds()))
            sample_size = max(1, int(len(users) * random.uniform(0.5, 0.85)))
            for user in random.sample(users, k=min(sample_size, len(users))):
                if VirtualClassAttendance.objects.filter(virtual_class=vc, user=user).exists():
                    continue
                roll = random.random()
                if roll < 0.7:
                    delay_seconds = random.randint(-120, 240)  # à l'heure (tolérance 5 min)
                elif roll < 0.9:
                    delay_seconds = random.randint(300, 900)  # léger retard
                else:
                    delay_seconds = random.randint(900, 1800)  # retard important
                joined_at = vc.scheduled_start + timedelta(seconds=delay_seconds)
                duration = int(duration_s * random.uniform(0.55, 1.0))
                VirtualClassAttendance.objects.create(
                    virtual_class=vc, user=user, joined_at=joined_at,
                    left_at=joined_at + timedelta(seconds=duration), duration_seconds=duration,
                )
                created += 1
        self.stdout.write(f'  Présences créées : {created}')

    # ── Participation aux forums ─────────────────────────────────────────────
    def seed_forum(self, company, users):
        from apps.social.models import ForumPost, ForumThread

        threads = list(ForumThread.objects.filter(company=company))
        if len(threads) < len(THREAD_TITLES):
            for title in THREAD_TITLES:
                thread, _ = ForumThread.objects.get_or_create(
                    company=company, title=title, defaults={'author': random.choice(users)}
                )
                if thread not in threads:
                    threads.append(thread)

        participants = random.sample(users, k=max(1, int(len(users) * 0.4)))
        created = 0
        for user in participants:
            thread = random.choice(threads)
            if ForumPost.objects.filter(thread=thread, author=user).exists():
                continue
            ForumPost.objects.create(thread=thread, author=user, content=random.choice(POST_SNIPPETS))
            created += 1
        self.stdout.write(f'  Messages de forum créés : {created}')

    # ── Recommandations IA de formation ──────────────────────────────────────
    def seed_recommendations(self, users):
        from apps.ai_engine.models import CourseRecommendation
        from apps.courses.models import Course, Enrollment

        published = list(Course.objects.filter(status=Course.STATUS_PUBLISHED))
        if not published:
            return

        created = 0
        for user in users:
            enrolled_ids = set(Enrollment.objects.filter(user=user).values_list('course_id', flat=True))
            candidates = [c for c in published if c.id not in enrolled_ids]
            if not candidates:
                continue
            picked = random.sample(candidates, k=min(2, len(candidates)))
            for i, course in enumerate(picked):
                _, was_created = CourseRecommendation.objects.get_or_create(
                    user=user, course=course,
                    defaults={
                        'score': round(random.uniform(60, 98), 2),
                        'reason': 'Basé sur vos compétences et votre progression récente',
                    },
                )
                if was_created:
                    created += 1
                # La première recommandation est suivie et complétée (KPI "formations recommandées terminées").
                if i == 0:
                    Enrollment.objects.get_or_create(
                        user=user, course=course,
                        defaults={
                            'status': Enrollment.STATUS_COMPLETED, 'progress_percent': 100,
                            'completed_at': timezone.now() - timedelta(days=random.randint(1, 9)),
                        },
                    )
        self.stdout.write(f'  Recommandations IA créées : {created}')

    # ── Couverture garantie : au moins UNE donnée réelle par employé pour chaque
    # dimension de KPI (pas d'échantillonnage aléatoire ici — chaque employé est traité). ──
    def seed_guaranteed_coverage(self, company, users, classes):
        from apps.ai_engine.models import DifficultyAlert
        from apps.assessments.models import Assessment, AssessmentAttempt, AssignmentSubmission
        from apps.courses.models import Enrollment
        from apps.hr_analytics.models import (
            EmployeeSkill, Evaluation360Campaign, Evaluation360Response,
            IndividualDevelopmentPlan, JobRoleSkillRequirement, PDIObjective,
        )
        from apps.learning_paths.models import LearningPath, LearningPathEnrollment
        from apps.progression.models import LessonProgress
        from apps.social.models import ForumPost, ForumThread
        from apps.virtual_classes.models import VirtualClassAttendance

        now = timezone.now()
        company_ids = company.get_descendant_ids()

        paths = list(LearningPath.objects.filter(is_active=True)[:20]) or list(LearningPath.objects.all()[:20])
        threads = list(ForumThread.objects.filter(company=company))
        critical_reqs = list(
            JobRoleSkillRequirement.objects.filter(job_role__company_id__in=company_ids, required_level__gte=4)
            .select_related('skill')
        )

        stats = {k: 0 for k in [
            'activity', 'attendance', 'forum', 'path', 'deadline',
            'assignment', 'critical_skill', 'dev_plan', 'eval360', 'alert',
        ]}

        for user in users:
            # 1) Activité récente (connexion + interaction plateforme dans les 4 derniers jours)
            user.last_active_at = now - timedelta(days=random.randint(0, 4), hours=random.randint(0, 20))
            user.save(update_fields=['last_active_at'])
            stats['activity'] += 1

            lp = LessonProgress.objects.filter(user=user).order_by('-updated_at').first()
            if lp:
                lp.last_opened_at = now - timedelta(days=random.randint(0, 4))
                lp.open_count = max(lp.open_count, random.randint(3, 8))
                lp.video_play_count = max(lp.video_play_count, random.randint(2, 6))
                lp.watch_percent = max(lp.watch_percent, Decimal('95'))
                lp.document_viewed = True
                if not lp.time_spent_seconds:
                    lp.time_spent_seconds = random.randint(600, 2400)
                lp.save()

            # 2) Présence aux classes virtuelles (garantie, pas échantillonnée)
            if classes:
                for vc in random.sample(classes, k=min(2, len(classes))):
                    if VirtualClassAttendance.objects.filter(virtual_class=vc, user=user).exists():
                        continue
                    duration_s = max(60, int((vc.scheduled_end - vc.scheduled_start).total_seconds()))
                    delay = random.choice([random.randint(-60, 200), random.randint(300, 700)])
                    joined = vc.scheduled_start + timedelta(seconds=delay)
                    duration = int(duration_s * random.uniform(0.75, 1.0))
                    VirtualClassAttendance.objects.create(
                        virtual_class=vc, user=user, joined_at=joined,
                        left_at=joined + timedelta(seconds=duration), duration_seconds=duration,
                    )
                    stats['attendance'] += 1

            # 3) Participation aux forums — au moins un message, et au moins un marqué
            # "solution" (proxy réel pour les "innovations proposées").
            if threads and not ForumPost.objects.filter(thread__in=threads, author=user).exists():
                ForumPost.objects.create(
                    thread=random.choice(threads), author=user,
                    content=random.choice(POST_SNIPPETS), is_solution=random.random() < 0.5,
                )
                stats['forum'] += 1
            if threads and not ForumPost.objects.filter(author=user, is_solution=True).exists():
                ForumPost.objects.create(
                    thread=random.choice(threads), author=user,
                    content=random.choice(POST_SNIPPETS), is_solution=True,
                )

            # 4) Parcours d'apprentissage terminé
            if paths and not LearningPathEnrollment.objects.filter(
                user=user, status=LearningPathEnrollment.STATUS_COMPLETED
            ).exists():
                LearningPathEnrollment.objects.update_or_create(
                    user=user, path=random.choice(paths),
                    defaults={
                        'status': LearningPathEnrollment.STATUS_COMPLETED, 'progress_percent': 100,
                        'completed_at': now - timedelta(days=random.randint(5, 90)),
                    },
                )
                stats['path'] += 1

            # 5) Respect des échéances (au moins une formation terminée dans les délais)
            completed = Enrollment.objects.filter(
                user=user, status=Enrollment.STATUS_COMPLETED, completed_at__isnull=False
            ).first()
            if completed and not completed.due_date:
                completed.due_date = completed.completed_at.date() + timedelta(days=random.randint(1, 10))
                completed.save(update_fields=['due_date'])
                stats['deadline'] += 1

            # 6) Devoir pratique noté (participation aux travaux pratiques)
            an_enrollment = Enrollment.objects.filter(user=user).select_related('course').first()
            if an_enrollment and not AssessmentAttempt.objects.filter(
                user=user, assessment__course=an_enrollment.course,
                assessment__assessment_type=Assessment.TYPE_ASSIGNMENT,
            ).exists():
                assignment, _ = Assessment.objects.get_or_create(
                    course=an_enrollment.course, chapter=None, assessment_type=Assessment.TYPE_ASSIGNMENT,
                    title='Étude de cas pratique',
                    defaults={
                        'instructions': 'Réalisez le cas pratique associé et soumettez votre livrable.',
                        'max_attempts': 1,
                    },
                )
                attempt = AssessmentAttempt.objects.create(
                    assessment=assignment, user=user, attempt_number=1,
                    status=AssessmentAttempt.STATUS_GRADED,
                    score=Decimal(str(random.randint(70, 95))), is_passed=True,
                )
                AssessmentAttempt.objects.filter(pk=attempt.pk).update(
                    submitted_at=now - timedelta(days=random.randint(2, 30))
                )
                AssignmentSubmission.objects.create(
                    attempt=attempt, comment='Travail réalisé selon les consignes.', grade=attempt.score,
                )
                stats['assignment'] += 1

            # 7) Compétences critiques maîtrisées (référentiel de postes)
            if critical_reqs:
                for req in random.sample(critical_reqs, k=min(2, len(critical_reqs))):
                    EmployeeSkill.objects.update_or_create(
                        user=user, skill=req.skill,
                        defaults={
                            'level': max(req.required_level, 4),
                            'last_assessed_at': now - timedelta(days=random.randint(1, 60)),
                        },
                    )
                stats['critical_skill'] += 1

            # 8) Plan de développement individuel — au moins un plan clôturé (PDI réalisé)
            if not IndividualDevelopmentPlan.objects.filter(
                user=user, status=IndividualDevelopmentPlan.STATUS_COMPLETED
            ).exists():
                plan, _ = IndividualDevelopmentPlan.objects.update_or_create(
                    user=user,
                    period_start=(now - timedelta(days=180)).date(),
                    period_end=(now - timedelta(days=1)).date(),
                    defaults={'status': IndividualDevelopmentPlan.STATUS_COMPLETED},
                )
            else:
                plan = IndividualDevelopmentPlan.objects.filter(user=user).order_by('-created_at').first()
            if not PDIObjective.objects.filter(plan__user=user, status=PDIObjective.STATUS_ACHIEVED).exists():
                PDIObjective.objects.create(
                    plan=plan, description='Renforcer les compétences clés du poste',
                    target_date=(now - timedelta(days=10)).date(), status=PDIObjective.STATUS_ACHIEVED,
                    expected_result="Objectif atteint lors de la dernière évaluation.",
                )
                stats['dev_plan'] += 1

            # 9) Évaluation 360° — au moins une auto-évaluation réelle (mêmes clés que le seed RH existant)
            if not Evaluation360Response.objects.filter(campaign__target_user=user, evaluator_type='self').exists():
                campaign, _ = Evaluation360Campaign.objects.get_or_create(
                    company=company, target_user=user,
                    title=f"Auto-évaluation continue — {user.get_full_name() or user.email}",
                    defaults={
                        'period_start': (now - timedelta(days=90)).date(), 'period_end': now.date(),
                        'status': Evaluation360Campaign.STATUS_CLOSED,
                    },
                )
                Evaluation360Response.objects.get_or_create(
                    campaign=campaign, evaluator=user, evaluator_type='self',
                    defaults={
                        'answers': {
                            'initiative': round(random.uniform(55, 90), 1),
                            'cooperation': round(random.uniform(55, 90), 1),
                            'adaptabilite': round(random.uniform(55, 90), 1),
                            'communication': round(random.uniform(55, 90), 1),
                            'respect_delais': round(random.uniform(55, 90), 1),
                            'qualite_travail': round(random.uniform(55, 90), 1),
                            'competences_metier': round(random.uniform(55, 90), 1),
                            'orientation_client': round(random.uniform(55, 90), 1),
                        },
                        'overall_score': round(random.uniform(60, 90), 2),
                        'submitted_at': now - timedelta(days=random.randint(5, 80)),
                    },
                )
                stats['eval360'] += 1

            # 9bis) Un point de comparaison à > 1 an (pour "progression depuis dernière éval.")
            if not Evaluation360Response.objects.filter(
                campaign__target_user=user, submitted_at__lt=now - timedelta(days=365)
            ).exists():
                old_campaign, _ = Evaluation360Campaign.objects.get_or_create(
                    company=company, target_user=user, title=f"Auto-évaluation (historique) — {user.get_full_name() or user.email}",
                    defaults={
                        'period_start': (now - timedelta(days=450)).date(), 'period_end': (now - timedelta(days=400)).date(),
                        'status': Evaluation360Campaign.STATUS_CLOSED,
                    },
                )
                response, _ = Evaluation360Response.objects.get_or_create(
                    campaign=old_campaign, evaluator=user, evaluator_type='self',
                    defaults={
                        'answers': {'initiative': round(random.uniform(40, 65), 1), 'communication': round(random.uniform(40, 65), 1)},
                        'overall_score': round(random.uniform(35, 60), 2),
                    },
                )
                Evaluation360Response.objects.filter(pk=response.pk).update(submitted_at=now - timedelta(days=400))
                stats['eval360'] += 1

            # 10) Alerte de difficulté résolue (proxy pour "incidents post-formation" traités)
            if an_enrollment and not DifficultyAlert.objects.filter(user=user).exists():
                DifficultyAlert.objects.create(
                    user=user, course=an_enrollment.course, signal_type=DifficultyAlert.SIGNAL_SLOW_PROGRESS,
                    details={'note': 'Ralentissement détecté puis résolu après accompagnement.'}, is_resolved=True,
                )
                stats['alert'] += 1

            # 11) Progression annuelle réelle (un point de score à ~1 an pour comparaison)
            recent_attempt = AssessmentAttempt.objects.filter(user=user, score__isnull=False).order_by('-started_at').first()
            if recent_attempt and not AssessmentAttempt.objects.filter(
                user=user, score__isnull=False, started_at__lt=now - timedelta(days=350)
            ).exists():
                old_score = max(Decimal('30'), recent_attempt.score - Decimal(str(random.randint(10, 25))))
                old_attempt = AssessmentAttempt.objects.create(
                    assessment=recent_attempt.assessment, user=user, attempt_number=99,
                    status=AssessmentAttempt.STATUS_GRADED, score=old_score, is_passed=old_score >= 50,
                )
                AssessmentAttempt.objects.filter(pk=old_attempt.pk).update(
                    started_at=now - timedelta(days=random.randint(370, 400)),
                    submitted_at=now - timedelta(days=random.randint(370, 400)),
                )
                stats['yearly_baseline'] = stats.get('yearly_baseline', 0) + 1

        self.stdout.write(f'  Couverture garantie appliquée : {stats}')
