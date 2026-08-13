"""Alimente l'agent IA RH avec du contenu réel : règlement intérieur (texte + PDF téléchargeable
+ vidéo), et parcours d'intégration (onboarding) par département/service pour chaque entreprise.
Idempotent : peut être relancé sans dupliquer les contenus déjà créés.
"""
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from apps.hr_agent.services import render_internal_rules_pdf

INTERNAL_RULES_SECTIONS = [
    (
        "Article 1 — Objet et champ d'application",
        "Le présent règlement intérieur a pour objet de définir les règles générales et permanentes relatives à "
        "la discipline, à l'hygiène et à la sécurité au sein de l'entreprise. Il s'applique à l'ensemble des "
        "collaborateurs, quel que soit leur statut ou leur affectation, ainsi qu'à toute personne présente dans "
        "les locaux de l'entreprise dans le cadre de son activité professionnelle.",
    ),
    (
        "Article 2 — Horaires de travail",
        "Les horaires de travail sont fixés par la direction en fonction des nécessités de service et affichés "
        "dans chaque département. Tout retard ou absence doit être signalé au responsable hiérarchique et au "
        "service RH dans les meilleurs délais. Trois retards non justifiés au cours d'un même mois font l'objet "
        "d'un entretien avec le responsable hiérarchique.",
    ),
    (
        "Article 3 — Congés et absences",
        "Les congés payés sont pris selon les modalités définies par la loi et les accords en vigueur, après "
        "validation du planning par le responsable hiérarchique. Toute absence pour maladie doit être justifiée "
        "par un certificat médical transmis au service RH dans un délai de 48 heures.",
    ),
    (
        "Article 4 — Hygiène et sécurité",
        "Chaque collaborateur est tenu de respecter les consignes de sécurité affichées dans les locaux, "
        "d'utiliser correctement les équipements mis à sa disposition et de signaler immédiatement toute "
        "situation dangereuse à son responsable ou au référent sécurité de l'entreprise.",
    ),
    (
        "Article 5 — Utilisation des outils numériques",
        "Les outils informatiques, la messagerie professionnelle et la plateforme de formation LMS PRO sont mis "
        "à disposition des collaborateurs dans le cadre de leur activité professionnelle. Un usage raisonnable à "
        "titre personnel est toléré dans la mesure où il ne nuit pas à l'activité et respecte la charte "
        "informatique de l'entreprise.",
    ),
    (
        "Article 6 — Respect et non-discrimination",
        "Tout comportement de harcèlement moral ou sexuel, de discrimination ou de violence est strictement "
        "interdit et fera l'objet de sanctions disciplinaires pouvant aller jusqu'au licenciement. Tout "
        "collaborateur témoin ou victime de tels agissements est invité à en informer sans délai le service RH.",
    ),
    (
        "Article 7 — Discipline générale",
        "Tout manquement aux dispositions du présent règlement est susceptible d'entraîner une sanction "
        "disciplinaire proportionnée à la gravité des faits, dans le respect de la procédure légale applicable "
        "(avertissement, mise à pied, licenciement selon les cas).",
    ),
]

ONBOARDING_INTRO = (
    "Bienvenue dans l'entreprise ! Ce parcours d'intégration vous accompagne durant vos premières semaines : "
    "présentation de l'équipe, outils à prendre en main, et personnes-ressources à contacter pour toute question."
)


def _onboarding_text(department_name):
    return (
        f"Bienvenue au sein du département {department_name} !\n\n"
        f"Durant votre première semaine, votre responsable hiérarchique vous présentera l'organisation du "
        f"département {department_name}, ses missions principales et vos interlocuteurs clés. "
        "N'hésitez pas à consulter les formations recommandées sur votre tableau de bord et à solliciter votre "
        "manager ou le service RH pour toute question sur vos outils, vos objectifs ou votre plan de développement "
        "individuel. Une réunion de suivi d'intégration est généralement organisée à 30, 60 et 90 jours."
    )


class Command(BaseCommand):
    help = "Alimente l'agent IA RH : règlement intérieur (texte + PDF) et contenus d'intégration par département."

    def add_arguments(self, parser):
        parser.add_argument('--company', type=int, default=None, help="ID entreprise racine (défaut : toutes)")

    def handle(self, *args, **options):
        from apps.tenants.models import Company

        company_id = options.get('company')
        companies = Company.objects.filter(pk=company_id) if company_id else Company.objects.filter(parent__isnull=True)

        for company in companies:
            self.stdout.write(self.style.MIGRATE_HEADING(f'--- {company.name} ---'))
            self.seed_internal_rules(company)
            self.seed_onboarding(company)

        self.stdout.write(self.style.SUCCESS('Terminé.'))

    def seed_internal_rules(self, company):
        from apps.hr_agent.models import AgentResource

        full_text = '\n\n'.join(f'{heading}\n{body}' for heading, body in INTERNAL_RULES_SECTIONS)

        text_resource, created_text = AgentResource.objects.update_or_create(
            company=company, category=AgentResource.CATEGORY_INTERNAL_RULES, content_type=AgentResource.TYPE_TEXT,
            department=None, service=None,
            defaults={
                'title': "Règlement intérieur — présentation",
                'text_body': full_text,
                'keywords': 'règlement intérieur, discipline, horaires, congés, sécurité, harcèlement',
                'order': 1,
                'is_active': True,
            },
        )

        pdf_resource, _ = AgentResource.objects.update_or_create(
            company=company, category=AgentResource.CATEGORY_INTERNAL_RULES, content_type=AgentResource.TYPE_PDF,
            department=None, service=None,
            defaults={
                'title': "Règlement intérieur (PDF téléchargeable)",
                'keywords': 'règlement intérieur, pdf, télécharger',
                'order': 2,
                'is_active': True,
            },
        )
        if not pdf_resource.file:
            pdf_bytes = render_internal_rules_pdf(company.name, INTERNAL_RULES_SECTIONS)
            pdf_resource.file.save(f'reglement_interieur_{company.id}.pdf', ContentFile(pdf_bytes), save=True)

        video_resource, _ = AgentResource.objects.update_or_create(
            company=company, category=AgentResource.CATEGORY_INTERNAL_RULES, content_type=AgentResource.TYPE_VIDEO,
            department=None, service=None,
            defaults={
                'title': "Présentation vidéo du règlement intérieur",
                'text_body': (
                    "Vidéo de présentation à téléverser par les RH (Gestion RH → Assistant IA RH). "
                    "En attendant, consultez la version texte et le PDF téléchargeable ci-dessus."
                ),
                'keywords': 'règlement intérieur, vidéo',
                'order': 3,
                'is_active': True,
            },
        )
        self.stdout.write(f'  Règlement intérieur : texte / PDF / vidéo (OK)')

    def seed_onboarding(self, company):
        from apps.hr_agent.models import AgentResource
        from apps.tenants.models import Department

        AgentResource.objects.update_or_create(
            company=company, category=AgentResource.CATEGORY_ONBOARDING, content_type=AgentResource.TYPE_TEXT,
            department=None, service=None,
            defaults={
                'title': "Intégration — bienvenue dans l'entreprise",
                'text_body': ONBOARDING_INTRO,
                'keywords': 'intégration, onboarding, bienvenue, nouvel employé, mentorat',
                'order': 1,
                'is_active': True,
            },
        )

        departments = Department.objects.filter(company_id__in=company.get_descendant_ids())
        created = 0
        for department in departments:
            _, was_created = AgentResource.objects.update_or_create(
                company=department.company, department=department, category=AgentResource.CATEGORY_ONBOARDING,
                content_type=AgentResource.TYPE_TEXT, service=None,
                defaults={
                    'title': f"Intégration — {department.name}",
                    'text_body': _onboarding_text(department.name),
                    'keywords': f'intégration, onboarding, mentorat, {department.name.lower()}',
                    'order': 2,
                    'is_active': True,
                },
            )
            if was_created:
                created += 1
        self.stdout.write(f'  Contenus d\'intégration par département : {departments.count()} département(s) couverts ({created} créés)')
