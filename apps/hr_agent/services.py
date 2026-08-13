"""Génération de documents PDF pour l'agent IA RH (règlement intérieur, fiche de poste)
et logique de l'agent (retrouver un contenu pertinent, détecter une demande de fiche de poste)."""
import io
import unicodedata

from django.core.files.base import ContentFile
from django.db.models import Q
from django.utils import timezone


def _normalize(text):
    """Minuscule et sans accents, pour un matching robuste indépendant de la saisie."""
    text = (text or '').lower()
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas

ACCENT = colors.HexColor('#4338ca')
INK = colors.HexColor('#1e293b')
MUTED = colors.HexColor('#64748b')


def render_document_pdf(*, title, subtitle, sections, org_name='', footer_note=''):
    """Rendu générique d'un document structuré (titre + sections titre/paragraphe).
    `sections` : liste de tuples (heading, paragraph_text)."""
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 56
    max_width = width - 2 * margin
    y = height - 70

    if org_name:
        pdf.setFont('Helvetica-Bold', 10)
        pdf.setFillColor(MUTED)
        pdf.drawString(margin, y, org_name.upper())
        y -= 26

    pdf.setFont('Helvetica-Bold', 22)
    pdf.setFillColor(ACCENT)
    for line in simpleSplit(title, 'Helvetica-Bold', 22, max_width):
        pdf.drawString(margin, y, line)
        y -= 26

    if subtitle:
        pdf.setFont('Helvetica', 11)
        pdf.setFillColor(MUTED)
        pdf.drawString(margin, y, subtitle)
        y -= 20

    pdf.setStrokeColor(colors.HexColor('#e2e8f0'))
    pdf.setLineWidth(1)
    pdf.line(margin, y, width - margin, y)
    y -= 30

    def new_page():
        nonlocal y
        pdf.showPage()
        y = height - 60

    for heading, paragraph in sections:
        if y < 110:
            new_page()
        if heading:
            pdf.setFont('Helvetica-Bold', 13)
            pdf.setFillColor(INK)
            for line in simpleSplit(heading, 'Helvetica-Bold', 13, max_width):
                if y < 90:
                    new_page()
                pdf.drawString(margin, y, line)
                y -= 18
            y -= 4
        pdf.setFont('Helvetica', 10.5)
        pdf.setFillColor(colors.HexColor('#334155'))
        for line in simpleSplit(paragraph or '', 'Helvetica', 10.5, max_width):
            if y < 80:
                new_page()
            pdf.drawString(margin, y, line)
            y -= 15
        y -= 18

    pdf.setFont('Helvetica', 8)
    pdf.setFillColor(MUTED)
    pdf.drawString(margin, 36, footer_note or f"Document généré le {timezone.now():%d/%m/%Y}")
    pdf.drawRightString(width - margin, 36, 'LMS PRO — Assistant IA RH')

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()


def render_internal_rules_pdf(company_name, sections):
    return render_document_pdf(
        title="Règlement Intérieur",
        subtitle="Document de référence — droits, devoirs et organisation du travail",
        sections=sections,
        org_name=company_name,
        footer_note="Règlement intérieur — document confidentiel, usage interne uniquement.",
    )


def render_job_description_pdf(job_request):
    sections = [
        ("Titulaire du poste", job_request.full_name),
        ("Intitulé du poste", job_request.job_title),
    ]
    if job_request.department_name:
        sections.append(("Département / Service", job_request.department_name))
    if job_request.manager_name:
        sections.append(("Responsable hiérarchique", job_request.manager_name))
    if job_request.start_date:
        sections.append(("Date de prise de poste", job_request.start_date.strftime('%d/%m/%Y')))

    missions = job_request.missions or []
    if missions:
        missions_text = '\n'.join(f'• {m}' for m in missions)
    else:
        missions_text = "Missions à préciser avec votre responsable hiérarchique."
    sections.append(("Missions principales", missions_text))

    org_name = job_request.user.company.name if job_request.user.company_id else ''
    return render_document_pdf(
        title="Fiche de Poste",
        subtitle=f"Générée automatiquement le {timezone.now():%d/%m/%Y} via l'Assistant IA RH",
        sections=sections,
        org_name=org_name,
        footer_note="Fiche de poste générée à la demande de l'employé — à valider avec les RH.",
    )


def generate_job_description(user, *, full_name, job_title, department_name='', manager_name='', start_date=None, missions=None):
    from apps.hr_agent.models import JobDescriptionRequest

    job_request = JobDescriptionRequest.objects.create(
        user=user, full_name=full_name, job_title=job_title, department_name=department_name,
        manager_name=manager_name, start_date=start_date, missions=missions or [],
    )
    pdf_bytes = render_job_description_pdf(job_request)
    filename = f"fiche_de_poste_{user.id}_{job_request.id}.pdf"
    job_request.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
    return job_request


# ─── Logique de l'agent : recherche de contenu pertinent + détection d'intention ──
JOB_DESCRIPTION_TRIGGERS = [
    'fiche de poste', 'fiche poste', 'ma fiche', 'poste de travail', 'job description',
]
RULES_TRIGGERS = ['reglement interieur', 'reglement']
ONBOARDING_TRIGGERS = ['integration', 'onboarding', 'mentorat', 'nouvel employe', 'nouveau employe', 'accueil']


def detect_intent(message):
    text = _normalize(message)
    if any(t in text for t in JOB_DESCRIPTION_TRIGGERS):
        return 'job_description'
    if any(t in text for t in RULES_TRIGGERS):
        return 'internal_rules'
    if any(t in text for t in ONBOARDING_TRIGGERS):
        return 'onboarding'
    return 'search'


def _resolve_scope_company_ids(user):
    """Périmètre entreprise (racine + toutes ses filiales) auquel appartient cet utilisateur —
    peu importe qu'il soit rattaché à la maison-mère ou à une filiale."""
    if not user.company_id:
        return set()
    company = user.company
    root = company.parent or company
    return root.get_descendant_ids()


def find_resources(user, message, category=None):
    """Retourne les contenus pertinents pour cet utilisateur : ceux de son entreprise (ou globaux),
    et scopés à son département/service (ou valables pour toute l'entreprise)."""
    from apps.hr_agent.models import AgentResource

    qs = AgentResource.objects.filter(is_active=True).filter(
        Q(company_id__in=_resolve_scope_company_ids(user)) | Q(company__isnull=True)
    ).filter(
        Q(department__isnull=True, service__isnull=True)
        | Q(department_id=user.department_id, service__isnull=True)
        | Q(service_id=user.service_id)
    )
    if category:
        qs = qs.filter(category=category)

    text = _normalize(message)
    words = [w for w in text.replace(',', ' ').split() if len(w) > 2]
    if not words or category:
        return list(qs.order_by('order')[:6])

    scored = []
    for resource in qs:
        haystack = _normalize(f"{resource.title} {resource.keywords} {resource.text_body}")
        score = sum(1 for w in words if w in haystack)
        if score > 0:
            scored.append((score, resource))
    scored.sort(key=lambda pair: -pair[0])
    return [r for _score, r in scored[:6]]
