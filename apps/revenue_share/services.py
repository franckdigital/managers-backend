import calendar
from datetime import datetime
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from apps.payments.models import Order, OrderItem
from apps.progression.models import XAPIStatement
from apps.revenue_share.models import PartnerMonthlyEarning, PartnerPayout, PartnerPayoutItem

ZERO = Decimal('0')


def _period_bounds(year, month):
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime(year, month, 1), tz)
    last_day = calendar.monthrange(year, month)[1]
    end = timezone.make_aware(datetime(year, month, last_day, 23, 59, 59, 999999), tz)
    return start, end


def _course_engagement(course_ids, start, end):
    """{course_id: views + clicks} for the period — 'vue' = course page opened,
    'clic' = a lesson video started/resumed (per the confirmed definitions), both
    already logged as XAPIStatement rows by apps.progression.services."""
    from apps.courses.models import Lesson

    engagement = {cid: 0 for cid in course_ids}

    view_rows = (
        XAPIStatement.objects
        .filter(object_type='course', object_id__in=[str(c) for c in course_ids],
                result__verb_detail='view', timestamp__range=(start, end))
        .values('object_id').annotate(n=Count('id'))
    )
    for row in view_rows:
        engagement[int(row['object_id'])] = engagement.get(int(row['object_id']), 0) + row['n']

    lesson_to_course = dict(
        Lesson.objects.filter(chapter__section__course_id__in=course_ids)
        .values_list('id', 'chapter__section__course_id')
    )
    if lesson_to_course:
        click_rows = (
            XAPIStatement.objects
            .filter(object_type='lesson', object_id__in=[str(l) for l in lesson_to_course],
                    result__verb_detail__in=['play', 'resume'], timestamp__range=(start, end))
            .values('object_id').annotate(n=Count('id'))
        )
        for row in click_rows:
            course_id = lesson_to_course.get(int(row['object_id']))
            if course_id is not None:
                engagement[course_id] = engagement.get(course_id, 0) + row['n']

    return engagement


def _view_click_split(course_ids, start, end):
    """Same as _course_engagement but returns (views, clicks) separately, for
    display on PartnerMonthlyEarning.view_count/click_count."""
    from apps.courses.models import Lesson

    views = {cid: 0 for cid in course_ids}
    clicks = {cid: 0 for cid in course_ids}

    view_rows = (
        XAPIStatement.objects
        .filter(object_type='course', object_id__in=[str(c) for c in course_ids],
                result__verb_detail='view', timestamp__range=(start, end))
        .values('object_id').annotate(n=Count('id'))
    )
    for row in view_rows:
        views[int(row['object_id'])] = row['n']

    lesson_to_course = dict(
        Lesson.objects.filter(chapter__section__course_id__in=course_ids)
        .values_list('id', 'chapter__section__course_id')
    )
    if lesson_to_course:
        click_rows = (
            XAPIStatement.objects
            .filter(object_type='lesson', object_id__in=[str(l) for l in lesson_to_course],
                    result__verb_detail__in=['play', 'resume'], timestamp__range=(start, end))
            .values('object_id').annotate(n=Count('id'))
        )
        for row in click_rows:
            course_id = lesson_to_course.get(int(row['object_id']))
            if course_id is not None:
                clicks[course_id] = clicks.get(course_id, 0) + row['n']

    return views, clicks


def _direct_revenue(course_ids, start, end):
    rows = (
        OrderItem.objects
        .filter(course_id__in=course_ids, order__status=Order.STATUS_PAID,
                order__order_type=Order.TYPE_COURSE_PURCHASE, order__paid_at__range=(start, end))
        .values('course_id').annotate(total=Sum('unit_price'))
    )
    return {row['course_id']: row['total'] or ZERO for row in rows}


def _bundle_share_revenue(course_ids, start, end, engagement):
    result = {cid: ZERO for cid in course_ids}
    course_id_set = set(course_ids)

    bundle_items = (
        OrderItem.objects
        .filter(bundle_id__isnull=False, order__status=Order.STATUS_PAID,
                order__order_type=Order.TYPE_COURSE_PURCHASE, order__paid_at__range=(start, end))
        .select_related('bundle').prefetch_related('bundle__courses')
    )
    for item in bundle_items:
        bundle_course_ids = list(item.bundle.courses.values_list('id', flat=True))
        relevant = [cid for cid in bundle_course_ids if cid in course_id_set]
        if not relevant or not bundle_course_ids:
            continue
        total_engagement = sum(engagement.get(cid, 0) for cid in bundle_course_ids)
        if total_engagement > 0:
            for cid in relevant:
                share = Decimal(engagement.get(cid, 0)) / Decimal(total_engagement)
                result[cid] += (item.unit_price * share)
        else:
            even_share = item.unit_price / len(bundle_course_ids)
            for cid in relevant:
                result[cid] += even_share

    return result


def _subscription_pool(start, end):
    total = (
        OrderItem.objects
        .filter(order__status=Order.STATUS_PAID, order__order_type=Order.TYPE_SUBSCRIPTION,
                order__paid_at__range=(start, end))
        .aggregate(total=Sum('unit_price'))['total']
    )
    return total or ZERO


@transaction.atomic
def compute_period(year, month):
    """Closes one calendar month: computes and stores an immutable PartnerMonthlyEarning
    row for every published course that has a revenue_partner + revenue_share_rate set.
    Idempotent — re-running the same period recomputes (update_or_create) rather than
    duplicating, since nothing is claimable until a PartnerPayoutItem locks a row in."""
    from apps.core.models import PlatformSettings
    from apps.courses.models import Course

    launch_date = PlatformSettings.get_solo().revenue_share_launch_date
    if launch_date and (year, month) < (launch_date.year, launch_date.month):
        raise ValueError(
            f"Le partage de revenus n'est actif que depuis {launch_date.strftime('%m/%Y')} — "
            f"aucune donnée de vues n'existe avant cette date pour {month:02d}/{year}."
        )

    start, end = _period_bounds(year, month)

    all_published = Course.objects.filter(status=Course.STATUS_PUBLISHED)
    all_course_ids = list(all_published.values_list('id', flat=True))
    if not all_course_ids:
        return []

    engagement = _course_engagement(all_course_ids, start, end)
    views, clicks = _view_click_split(all_course_ids, start, end)
    total_catalog_engagement = sum(engagement.values())

    direct_revenue = _direct_revenue(all_course_ids, start, end)
    bundle_revenue = _bundle_share_revenue(all_course_ids, start, end, engagement)
    subscription_pool = _subscription_pool(start, end)

    results = []
    partner_courses = all_published.filter(
        revenue_partner__isnull=False, revenue_share_rate__isnull=False
    ).select_related('revenue_partner')

    for course in partner_courses:
        cid = course.id
        direct = direct_revenue.get(cid, ZERO)
        bundle_share = bundle_revenue.get(cid, ZERO)
        if total_catalog_engagement > 0:
            sub_share = subscription_pool * Decimal(engagement.get(cid, 0)) / Decimal(total_catalog_engagement)
        else:
            sub_share = ZERO

        total_revenue = direct + bundle_share + sub_share
        earning_amount = (total_revenue * course.revenue_share_rate / 100).quantize(Decimal('0.01'))

        earning, _created = PartnerMonthlyEarning.objects.update_or_create(
            course=course, year=year, month=month,
            defaults={
                'partner': course.revenue_partner,
                'rate': course.revenue_share_rate,
                'direct_revenue': direct.quantize(Decimal('0.01')),
                'subscription_share_revenue': sub_share.quantize(Decimal('0.01')),
                'bundle_share_revenue': bundle_share.quantize(Decimal('0.01')),
                'total_revenue': total_revenue.quantize(Decimal('0.01')),
                'earning_amount': earning_amount,
                'view_count': views.get(cid, 0),
                'click_count': clicks.get(cid, 0),
            },
        )
        results.append(earning)

    return results


def course_engagement_detail(course_id, year, month):
    """Per-user breakdown of views/clicks for one course/month — the 'traçabilité KPI'
    behind the aggregate view_count/click_count on PartnerMonthlyEarning: which student
    or employee generated the engagement, and when they last did."""
    from apps.courses.models import Lesson

    start, end = _period_bounds(year, month)
    by_user = {}

    def _touch(user_id, field, ts):
        row = by_user.setdefault(user_id, {'view_count': 0, 'click_count': 0, 'last_activity': ts})
        row[field] += 1
        if ts > row['last_activity']:
            row['last_activity'] = ts

    view_rows = (
        XAPIStatement.objects
        .filter(object_type='course', object_id=str(course_id), result__verb_detail='view',
                timestamp__range=(start, end))
        .values_list('user_id', 'timestamp')
    )
    for user_id, ts in view_rows:
        _touch(user_id, 'view_count', ts)

    lesson_ids = list(Lesson.objects.filter(chapter__section__course_id=course_id).values_list('id', flat=True))
    if lesson_ids:
        click_rows = (
            XAPIStatement.objects
            .filter(object_type='lesson', object_id__in=[str(l) for l in lesson_ids],
                    result__verb_detail__in=['play', 'resume'], timestamp__range=(start, end))
            .values_list('user_id', 'timestamp')
        )
        for user_id, ts in click_rows:
            _touch(user_id, 'click_count', ts)

    if not by_user:
        return []

    from apps.accounts.models import User
    users = {u.id: u for u in User.objects.filter(id__in=by_user.keys())}

    results = []
    for user_id, row in by_user.items():
        user = users.get(user_id)
        if not user:
            continue
        results.append({
            'user_id': user_id,
            'user_name': user.get_full_name() or user.email,
            'user_email': user.email,
            'user_role': user.role,
            'view_count': row['view_count'],
            'click_count': row['click_count'],
            'last_activity': row['last_activity'],
        })

    results.sort(key=lambda r: (r['view_count'] + r['click_count']), reverse=True)
    return results


def catalog_period_totals(year, month):
    """Total revenu (direct + bundles + part d'abonnement) de tout le catalogue publié pour
    ce mois, et la part de ce total déjà couverte par des cours liés à un partenaire — sert
    à afficher le revenu 'non attribué' (cours sans revenue_partner) dans le rapport admin."""
    from apps.courses.models import Course

    start, end = _period_bounds(year, month)

    all_published = Course.objects.filter(status=Course.STATUS_PUBLISHED)
    all_course_ids = list(all_published.values_list('id', flat=True))
    if not all_course_ids:
        return {'total_catalog_revenue': ZERO, 'partner_linked_revenue': ZERO, 'unattributed_revenue': ZERO}

    engagement = _course_engagement(all_course_ids, start, end)
    total_catalog_engagement = sum(engagement.values())

    direct_revenue = _direct_revenue(all_course_ids, start, end)
    bundle_revenue = _bundle_share_revenue(all_course_ids, start, end, engagement)
    subscription_pool = _subscription_pool(start, end)

    partner_course_ids = set(
        all_published.filter(revenue_partner__isnull=False, revenue_share_rate__isnull=False)
        .values_list('id', flat=True)
    )

    total_catalog_revenue = ZERO
    partner_linked_revenue = ZERO
    for cid in all_course_ids:
        direct = direct_revenue.get(cid, ZERO)
        bundle_share = bundle_revenue.get(cid, ZERO)
        if total_catalog_engagement > 0:
            sub_share = subscription_pool * Decimal(engagement.get(cid, 0)) / Decimal(total_catalog_engagement)
        else:
            sub_share = ZERO
        course_total = direct + bundle_share + sub_share
        total_catalog_revenue += course_total
        if cid in partner_course_ids:
            partner_linked_revenue += course_total

    return {
        'total_catalog_revenue': total_catalog_revenue.quantize(Decimal('0.01')),
        'partner_linked_revenue': partner_linked_revenue.quantize(Decimal('0.01')),
        'unattributed_revenue': (total_catalog_revenue - partner_linked_revenue).quantize(Decimal('0.01')),
    }


def partner_unpaid_earnings(partner):
    """PartnerMonthlyEarning rows for this partner not yet claimed by a payout —
    mirrors apps.payments.services.trainer_unpaid_earnings exactly."""
    return PartnerMonthlyEarning.objects.filter(
        partner=partner, payout_item__isnull=True
    ).select_related('course')


def request_partner_payout(partner):
    items = list(partner_unpaid_earnings(partner))
    if not items:
        raise ValueError('Aucun gain disponible pour une demande de paiement.')

    gross = sum((item.earning_amount for item in items), start=ZERO)

    with transaction.atomic():
        payout = PartnerPayout.objects.create(partner=partner, gross_amount=gross)
        PartnerPayoutItem.objects.bulk_create([
            PartnerPayoutItem(payout=payout, earning=item, amount=item.earning_amount) for item in items
        ])
    return payout


def approve_partner_payout(payout, admin_user):
    payout.status = PartnerPayout.STATUS_APPROVED
    payout.processed_by = admin_user
    payout.save(update_fields=['status', 'processed_by'])
    return payout


def mark_partner_payout_paid(payout, admin_user):
    payout.status = PartnerPayout.STATUS_PAID
    payout.processed_by = admin_user
    payout.processed_at = timezone.now()
    payout.save(update_fields=['status', 'processed_by', 'processed_at'])
    return payout


def reject_partner_payout(payout, admin_user, notes=''):
    with transaction.atomic():
        payout.items.all().delete()
        payout.status = PartnerPayout.STATUS_REJECTED
        payout.processed_by = admin_user
        payout.processed_at = timezone.now()
        payout.notes = notes
        payout.save(update_fields=['status', 'processed_by', 'processed_at', 'notes'])
    return payout
