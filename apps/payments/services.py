import io
from decimal import Decimal

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from apps.payments.models import Invoice, Order, OrderItem, Payment, Payout, PayoutItem
from apps.payments.providers import get_provider


def create_order_from_cart(user, cart, coupon=None):
    items = list(cart.items.select_related('course', 'bundle'))
    if not items:
        raise ValueError('Le panier est vide')

    def item_price(item):
        return item.course.price if item.course else item.bundle.price

    def item_title(item):
        return item.course.title if item.course else item.bundle.title

    subtotal = sum((item_price(item) for item in items), start=0)
    discount = coupon.compute_discount(subtotal) if coupon and coupon.is_valid_now() else 0
    total = max(subtotal - discount, 0)

    with transaction.atomic():
        order = Order.objects.create(
            user=user,
            company=user.company,
            subtotal=subtotal,
            discount_amount=discount,
            total_amount=total,
            coupon=coupon if coupon and coupon.is_valid_now() else None,
        )
        for item in items:
            OrderItem.objects.create(
                order=order, course=item.course, bundle=item.bundle,
                title_snapshot=item_title(item), unit_price=item_price(item),
            )
        cart.items.all().delete()
    return order


def initiate_payment(order, provider_code):
    provider = get_provider(provider_code)
    result = provider.init_payment(order)
    payment = Payment.objects.create(
        order=order,
        provider=provider_code,
        provider_reference=result.provider_reference,
        amount=order.total_amount,
        currency=order.currency,
        raw_response=result.raw if isinstance(result.raw, dict) else {},
    )
    return payment, result


def create_subscription_order(user, company, plan):
    with transaction.atomic():
        order = Order.objects.create(
            user=user,
            company=company,
            order_type=Order.TYPE_SUBSCRIPTION,
            subtotal=plan.price,
            total_amount=plan.price,
            currency=plan.currency,
            subscription_plan=plan,
        )
        OrderItem.objects.create(
            order=order,
            title_snapshot=f'Abonnement {plan.name}',
            unit_price=plan.price,
        )
    return order


def mark_order_paid(order):
    from apps.courses.services import enroll_user_in_order_courses

    if order.status == Order.STATUS_PAID:
        return order

    order.status = Order.STATUS_PAID
    order.paid_at = timezone.now()
    order.save(update_fields=['status', 'paid_at'])

    if order.coupon:
        order.coupon.used_count += 1
        order.coupon.save(update_fields=['used_count'])

    if order.order_type == Order.TYPE_SUBSCRIPTION and order.subscription_plan_id:
        order_full = Order.objects.select_related('subscription_plan', 'company', 'user').get(pk=order.pk)
        if order_full.subscription_plan:
            if order_full.company:
                from apps.tenants.services import activate_company_subscription
                activate_company_subscription(
                    order_full.company, order_full.subscription_plan, amount_paid=order_full.total_amount
                )
            else:
                from apps.tenants.services import activate_user_subscription
                activate_user_subscription(
                    order_full.user, order_full.subscription_plan, amount_paid=order_full.total_amount
                )
    else:
        enroll_user_in_order_courses(order)

    generate_invoice(order)

    from apps.integrations.services import send_webhook
    from apps.notifications.services import notify_user

    send_webhook('order.paid', order.company, {'order_id': order.id, 'total_amount': str(order.total_amount)})
    notify_user(
        order.user,
        'Paiement confirmé',
        f"Votre paiement de {order.total_amount} {order.currency} a été confirmé. Bon apprentissage !",
        data={'order_id': order.id},
    )
    return order


def trainer_unpaid_earnings(trainer):
    """OrderItems from paid orders on the trainer's courses that have not yet been included
    in a payout request."""
    return OrderItem.objects.filter(
        course__instructor=trainer, order__status=Order.STATUS_PAID, payout_item__isnull=True
    ).select_related('order', 'course')


def request_payout(trainer):
    from apps.core.models import PlatformSettings

    items = list(trainer_unpaid_earnings(trainer))
    if not items:
        raise ValueError("Aucun revenu disponible pour une demande de paiement.")

    gross = sum((item.unit_price for item in items), start=0)
    rate = PlatformSettings.get_solo().default_commission_rate
    commission = (gross * rate / 100).quantize(Decimal('0.01'))
    net = gross - commission

    with transaction.atomic():
        payout = Payout.objects.create(
            trainer=trainer, gross_amount=gross, commission_rate=rate, commission_amount=commission, net_amount=net,
        )
        PayoutItem.objects.bulk_create([
            PayoutItem(payout=payout, order_item=item, amount=item.unit_price) for item in items
        ])
    return payout


def approve_payout(payout, admin_user):
    payout.status = Payout.STATUS_APPROVED
    payout.processed_by = admin_user
    payout.save(update_fields=['status', 'processed_by'])
    return payout


def mark_payout_paid(payout, admin_user):
    payout.status = Payout.STATUS_PAID
    payout.processed_by = admin_user
    payout.processed_at = timezone.now()
    payout.save(update_fields=['status', 'processed_by', 'processed_at'])
    return payout


def reject_payout(payout, admin_user, notes=''):
    with transaction.atomic():
        payout.items.all().delete()
        payout.status = Payout.STATUS_REJECTED
        payout.processed_by = admin_user
        payout.processed_at = timezone.now()
        payout.notes = notes
        payout.save(update_fields=['status', 'processed_by', 'processed_at', 'notes'])
    return payout


def generate_invoice(order):
    if hasattr(order, 'invoice'):
        return order.invoice
    number = f'INV-{order.id:08d}'
    invoice = Invoice.objects.create(order=order, invoice_number=number)
    _attach_invoice_pdf(invoice)
    return invoice


def _attach_invoice_pdf(invoice):
    order = invoice.order
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.setFont('Helvetica-Bold', 20)
    pdf.drawString(2 * cm, height - 2 * cm, 'Facture')

    pdf.setFont('Helvetica', 10)
    pdf.drawString(2 * cm, height - 3 * cm, f'N° {invoice.invoice_number}')
    pdf.drawString(2 * cm, height - 3.5 * cm, f'Date : {invoice.issued_at:%d/%m/%Y}')
    pdf.drawString(2 * cm, height - 4.2 * cm, f'Client : {order.user.get_full_name() or order.user.email}')
    if order.company:
        pdf.drawString(2 * cm, height - 4.7 * cm, f'Entreprise : {order.company.name}')

    y = height - 6 * cm
    pdf.setFont('Helvetica-Bold', 10)
    pdf.drawString(2 * cm, y, 'Désignation')
    pdf.drawString(15 * cm, y, 'Montant')
    pdf.line(2 * cm, y - 0.2 * cm, 19 * cm, y - 0.2 * cm)

    pdf.setFont('Helvetica', 10)
    y -= 0.8 * cm
    for item in order.items.all():
        pdf.drawString(2 * cm, y, item.title_snapshot[:80])
        pdf.drawString(15 * cm, y, f'{item.unit_price} {order.currency}')
        y -= 0.6 * cm

    y -= 0.4 * cm
    pdf.line(2 * cm, y, 19 * cm, y)
    y -= 0.6 * cm
    pdf.drawString(13 * cm, y, 'Sous-total')
    pdf.drawString(17 * cm, y, f'{order.subtotal} {order.currency}')
    y -= 0.6 * cm
    pdf.drawString(13 * cm, y, 'Remise')
    pdf.drawString(17 * cm, y, f'-{order.discount_amount} {order.currency}')
    y -= 0.6 * cm
    pdf.setFont('Helvetica-Bold', 10)
    pdf.drawString(13 * cm, y, 'Total payé')
    pdf.drawString(17 * cm, y, f'{order.total_amount} {order.currency}')

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    invoice.pdf_file.save(f'{invoice.invoice_number}.pdf', ContentFile(buffer.getvalue()), save=True)
