import hashlib
import hmac
import io
import secrets

import qrcode
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas

from apps.certificates.models import Certificate, CertificateTemplate


def sign_certificate(certificate_number, verification_code):
    message = f'{certificate_number}:{verification_code}'.encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


def resolve_template(user):
    """Choisit le CertificateTemplate a utiliser pour un utilisateur donne.
    Priorite : le template actif propre a son entreprise, sinon le template global par defaut."""
    company = getattr(user, 'company', None)
    if company is not None:
        company_template = (
            CertificateTemplate.objects.filter(company=company, is_active=True).order_by('-updated_at').first()
        )
        if company_template:
            return company_template
    return (
        CertificateTemplate.objects
        .filter(company__isnull=True, is_default=True, is_active=True)
        .order_by('-updated_at')
        .first()
    )


def generate_certificate(user, course=None, path=None, template=None):
    template = template or resolve_template(user)
    certificate_number = f'LMSPRO-{secrets.token_hex(6).upper()}'
    verification_code = secrets.token_urlsafe(16)

    certificate = Certificate.objects.create(
        user=user,
        course=course,
        path=path,
        template=template,
        certificate_number=certificate_number,
        verification_code=verification_code,
    )
    certificate.digital_signature = sign_certificate(certificate_number, verification_code)
    certificate.save(update_fields=['digital_signature'])

    _attach_qr_code(certificate)
    _attach_pdf(certificate)

    from apps.integrations.services import send_webhook
    from apps.notifications.services import notify_user

    send_webhook('certificate.issued', user.company, {
        'certificate_number': certificate.certificate_number,
        'user_id': user.id,
    })
    title = course.title if course else (path.title if path else '')
    notify_user(
        user,
        'Certificat délivré',
        f"Votre certificat pour « {title} » est disponible (N° {certificate.certificate_number}).",
        data={'certificate_id': certificate.id},
    )
    return certificate


def maybe_issue_certificate_for_course(user, course):
    """Issue the course certificate once the learner has both finished 100% of the lessons AND,
    if the course has a course-level final exam (an Assessment with chapter=None), scored 100%
    on it. Safe to call from multiple trigger points (lesson completion, exam grading) — no-ops
    if a certificate already exists or the conditions aren't met yet."""

    if not course.certificate_enabled:
        return None
    if Certificate.objects.filter(user=user, course=course).exists():
        return None

    from apps.courses.models import Enrollment

    try:
        enrollment = Enrollment.objects.get(user=user, course=course)
    except Enrollment.DoesNotExist:
        return None
    if enrollment.progress_percent < 100:
        return None

    from apps.assessments.models import Assessment, AssessmentAttempt

    final_exam = Assessment.objects.filter(course=course, chapter__isnull=True, is_published=True).first()
    if final_exam is not None:
        has_perfect_attempt = AssessmentAttempt.objects.filter(
            assessment=final_exam, user=user, score__gte=100
        ).exists()
        if not has_perfect_attempt:
            return None

    return generate_certificate(user, course=course)


def _verification_url(certificate):
    return f'{settings.FRONTEND_BASE_URL}/verify-certificate/{certificate.verification_code}'


def _attach_qr_code(certificate):
    img = qrcode.make(_verification_url(certificate))
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    certificate.qr_code_image.save(f'{certificate.certificate_number}.png', ContentFile(buffer.getvalue()), save=True)


DEFAULT_TITLE_TEXT = 'CERTIFICAT DE FORMATION'
DEFAULT_INTRO_TEXT = 'Est décerné avec distinction à'
DEFAULT_BODY_PARAGRAPH = 'Pour avoir suivi avec succès la formation {course_title}.'
DEFAULT_ACCENT_COLOR = '#0F4C81'


class _SafeDict(dict):
    def __missing__(self, key):
        return ''


def _fit_image(path, box_w, box_h):
    """Calcule les dimensions (largeur, hauteur) d'une image redimensionnee proportionnellement
    pour rentrer dans une boite box_w x box_h, sans la deformer."""
    with Image.open(path) as img:
        img_w, img_h = img.size
    scale = min(box_w / img_w, box_h / img_h)
    return img_w * scale, img_h * scale


def _draw_signer(pdf, template, slot, x_center, image_bottom_y, text_y):
    name = getattr(template, f'signer{slot}_name', '') if template else ''
    title = getattr(template, f'signer{slot}_title', '') if template else ''
    signature = getattr(template, f'signer{slot}_signature', None) if template else None
    if not name and not title and not signature:
        return

    if signature:
        try:
            draw_w, draw_h = _fit_image(signature.path, 130, 45)
            pdf.drawImage(
                ImageReader(signature.path), x_center - draw_w / 2, image_bottom_y,
                width=draw_w, height=draw_h, mask='auto', preserveAspectRatio=True,
            )
        except (OSError, ValueError):
            pass

    label = ' I '.join(part for part in (name, title) if part)
    pdf.setFont('Helvetica', 10)
    pdf.setFillColor(colors.HexColor('#444444'))
    pdf.drawCentredString(x_center, text_y, label)
    pdf.setFillColor(colors.black)


def _draw_chevrons(pdf, x_start, x_end, y_center, point_right, size=9, gap=17, color=colors.white, line_width=2.2):
    pdf.setStrokeColor(color)
    pdf.setLineWidth(line_width)
    pdf.setLineCap(1)
    x = x_start
    while x < x_end:
        if point_right:
            pdf.line(x - size, y_center + size, x, y_center)
            pdf.line(x, y_center, x - size, y_center - size)
        else:
            pdf.line(x + size, y_center + size, x, y_center)
            pdf.line(x, y_center, x + size, y_center - size)
        x += gap


def _draw_frame(pdf, width, height, accent, thickness):
    pdf.setFillColor(accent)
    pdf.rect(0, 0, width, height, stroke=0, fill=1)
    pdf.setFillColor(colors.white)
    pdf.rect(thickness, thickness, width - 2 * thickness, height - 2 * thickness, stroke=0, fill=1)

    band_margin = thickness + 50
    _draw_chevrons(pdf, band_margin, width - band_margin, height - thickness / 2, point_right=True)
    _draw_chevrons(pdf, band_margin, width - band_margin, thickness / 2, point_right=False)
    pdf.setFillColor(colors.black)


def render_certificate_pdf(template, *, recipient_name, course_title, certificate_number, issued_at, qr_image_source=None):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)
    frame_thickness = 30
    inner_margin = frame_thickness + 50

    accent = colors.HexColor((template.accent_color if template else None) or DEFAULT_ACCENT_COLOR)

    background_image = template.background_image if (template and template.background_image) else None
    if background_image:
        try:
            pdf.drawImage(ImageReader(background_image.path), 0, 0, width=width, height=height, mask='auto')
        except (OSError, ValueError):
            background_image = None

    if not background_image:
        _draw_frame(pdf, width, height, accent, frame_thickness)

    # Espacements configurables (pt supplementaires entre blocs)
    gap_after_header = (template.gap_after_header if template else None) or 0
    gap_after_title = (template.gap_after_title if template else None) or 0
    gap_after_content = (template.gap_after_content if template else None) or 0

    # En-tete : nom d'organisme (texte seul, pas de logo image)
    org_name = template.org_name if template else ''
    org_name_fs = (template.org_name_font_size if template else None) or 15
    header_bottom_y = height - 65  # y de la 1ere ligne
    if org_name:
        words = org_name.split()
        first_line = ' '.join(words[:-1]).upper() if len(words) > 1 else org_name.upper()
        second_line = words[-1] if len(words) > 1 else ''
        pdf.setFont('Helvetica-Bold', org_name_fs)
        pdf.setFillColor(accent)
        pdf.drawCentredString(width / 2, header_bottom_y, first_line)
        if second_line:
            second_fs = max(8, org_name_fs - 5)
            pdf.setFont('Helvetica', second_fs)
            pdf.setFillColor(colors.HexColor('#6B7280'))
            header_bottom_y -= org_name_fs + 2
            pdf.drawCentredString(width / 2, header_bottom_y, second_line)

    # Titre
    title_text = template.title_text if template else DEFAULT_TITLE_TEXT
    title_fs = (template.title_font_size if template else None) or 28
    title_y = header_bottom_y - 46 - gap_after_header
    pdf.setFont('Helvetica-Bold', title_fs)
    pdf.setFillColor(accent)
    pdf.drawCentredString(width / 2, title_y, title_text)

    # Intro + nom du destinataire
    intro_text = template.intro_text if template else DEFAULT_INTRO_TEXT
    intro_fs = (template.intro_font_size if template else None) or 15
    intro_y = title_y - 83 - gap_after_title
    pdf.setFillColor(colors.HexColor('#555555'))
    pdf.setFont('Helvetica', intro_fs)
    pdf.drawCentredString(width / 2, intro_y, intro_text)

    pdf.setFont('Times-Italic', 38)
    pdf.setFillColor(accent)
    pdf.drawCentredString(width / 2, intro_y - 42, recipient_name)

    # Paragraphe (substitution de placeholders)
    context = _SafeDict({
        'recipient_name': recipient_name,
        'course_title': course_title,
        'date': issued_at.strftime('%d/%m/%Y'),
        'certificate_number': certificate_number,
        'org_name': org_name,
    })
    body_paragraph = (template.body_paragraph if template else DEFAULT_BODY_PARAGRAPH).format_map(context)
    body_fs = (template.body_font_size if template else None) or 14
    pdf.setFont('Helvetica', body_fs)
    pdf.setFillColor(colors.HexColor('#555555'))
    max_width = width - 2 * (inner_margin + 60)
    body_y = intro_y - 82
    last_body_y = body_y
    for line in simpleSplit(body_paragraph, 'Helvetica', body_fs, max_width):
        pdf.drawCentredString(width / 2, body_y, line)
        last_body_y = body_y
        body_y -= body_fs + 5

    # Signataires (gauche / droite) + QR code, alignes sur la meme bande horizontale
    signer_image_bottom_y = max(last_body_y - 80 - gap_after_content, frame_thickness + 85)
    signer_text_y = signer_image_bottom_y - 18
    _draw_signer(pdf, template, 1, width * 0.22, signer_image_bottom_y, signer_text_y)
    _draw_signer(pdf, template, 2, width * 0.78, signer_image_bottom_y, signer_text_y)

    if qr_image_source is not None:
        qr_size = 75
        qr_y = signer_image_bottom_y - (qr_size - 45) / 2
        pdf.drawImage(
            ImageReader(qr_image_source), width / 2 - qr_size / 2, qr_y,
            width=qr_size, height=qr_size, mask='auto',
        )

    # Pied de page
    footer_website = ''
    if template:
        footer_website = template.footer_website or (template.company.website if template.company_id else '')
    footer_y = frame_thickness + 18
    pdf.setFont('Helvetica', 8)
    pdf.setFillColor(colors.HexColor('#666666'))
    pdf.drawString(inner_margin - 20, footer_y, f'Certificat ID : {certificate_number}')
    if footer_website:
        pdf.drawCentredString(width / 2, footer_y, footer_website)
    pdf.drawRightString(width - inner_margin + 20, footer_y, f'Certifié le : {issued_at:%d/%m/%Y}')

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()


def _attach_pdf(certificate):
    template = certificate.template
    course_title = certificate.course.title if certificate.course else (certificate.path.title if certificate.path else '')
    recipient_name = certificate.user.get_full_name() or certificate.user.email
    qr_image_source = certificate.qr_code_image.path if certificate.qr_code_image else None
    pdf_bytes = render_certificate_pdf(
        template,
        recipient_name=recipient_name,
        course_title=course_title,
        certificate_number=certificate.certificate_number,
        issued_at=certificate.issued_at,
        qr_image_source=qr_image_source,
    )
    certificate.pdf_file.save(f'{certificate.certificate_number}.pdf', ContentFile(pdf_bytes), save=True)


def build_preview_pdf(template):
    """Genere un PDF d'exemple (donnees fictives) pour previsualiser un CertificateTemplate."""
    qr_buffer = io.BytesIO()
    qrcode.make('https://exemple.com/verify-certificate/APERCU').save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    return render_certificate_pdf(
        template,
        recipient_name='Jean Dupont',
        course_title='Formation Exemple',
        certificate_number='LMSPRO-APERCU01',
        issued_at=timezone.now(),
        qr_image_source=qr_buffer,
    )


def regenerate_all_certificates():
    """Recalcule le template applicable et regenere le PDF de chaque certificat existant.
    Appele apres creation/modification/suppression d'un CertificateTemplate pour que les
    certificats deja delivres reprennent immediatement le design a jour."""
    certificates = Certificate.objects.select_related('user', 'user__company', 'course', 'path')
    for certificate in certificates:
        resolved = resolve_template(certificate.user)
        if certificate.template_id != (resolved.id if resolved else None):
            certificate.template = resolved
            certificate.save(update_fields=['template'])
        if not certificate.qr_code_image:
            _attach_qr_code(certificate)
        _attach_pdf(certificate)


def verify_certificate(verification_code):
    try:
        certificate = Certificate.objects.select_related('user', 'course', 'path').get(verification_code=verification_code)
    except Certificate.DoesNotExist:
        return None

    expected_signature = sign_certificate(certificate.certificate_number, certificate.verification_code)
    is_authentic = hmac.compare_digest(expected_signature, certificate.digital_signature)
    return certificate, is_authentic and not certificate.is_revoked
