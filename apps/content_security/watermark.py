import io

from django.utils import timezone
from PIL import Image, ImageDraw
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas as rl_canvas


def watermark_text(user):
    return f'{user.get_full_name() or user.email} – {user.email} – {timezone.now():%Y-%m-%d %H:%M}'


def watermark_pdf(file_path, user):
    text = watermark_text(user)
    reader = PdfReader(file_path)
    writer = PdfWriter()

    for page in reader.pages:
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        packet = io.BytesIO()
        overlay_canvas = rl_canvas.Canvas(packet, pagesize=(width, height))
        overlay_canvas.setFont('Helvetica', 8)
        overlay_canvas.setFillColorRGB(0.6, 0.6, 0.6)
        overlay_canvas.drawString(20, 15, text)
        overlay_canvas.save()
        packet.seek(0)

        overlay_page = PdfReader(packet).pages[0]
        page.merge_page(overlay_page)
        writer.add_page(page)

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output


def watermark_image(file_path, user):
    text = watermark_text(user)
    image = Image.open(file_path).convert('RGBA')
    overlay = Image.new('RGBA', image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    draw.text((10, max(image.height - 24, 0)), text, fill=(255, 0, 0, 160))
    combined = Image.alpha_composite(image, overlay).convert('RGB')

    buffer = io.BytesIO()
    combined.save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer
