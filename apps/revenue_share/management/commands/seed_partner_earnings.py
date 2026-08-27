"""
Management command: seed_partner_earnings
Simulates student activity (views, clicks, direct purchases, and — if a subscription
plan exists — a subscription order) for the courses linked to one or all video
partners, so their revenue-share dashboard shows realistic numbers without waiting
for real traffic. By default also closes the target month right after seeding.

Usage:
    python manage.py seed_partner_earnings                          # all partners, current month
    python manage.py seed_partner_earnings --partner-email karim.ndiaye@exemple.com
    python manage.py seed_partner_earnings --year 2026 --month 8 --no-close
"""
import random
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

VIEWER_NAMES = [
    ('Fanta', 'Kaba'), ('Idrissa', 'Ouattara'), ('Nadège', 'Assamoi'),
    ('Yacouba', 'Diarra'), ('Rose', 'Kouyaté'), ('Salif', 'Bamba'),
    ('Awa', 'Sangaré'), ('Landry', 'Dosso'), ('Mireille', 'Tapé'),
    ('Ousmane', 'Fofana'),
]


def _slugify(name):
    replacements = {
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'â': 'a', 'à': 'a', 'ä': 'a',
        'î': 'i', 'ï': 'i',
        'ô': 'o', 'ö': 'o',
        'û': 'u', 'ü': 'u',
        'ç': 'c',
        '-': '', ' ': '',
    }
    result = name.lower()
    for src, dst in replacements.items():
        result = result.replace(src, dst)
    return result


class Command(BaseCommand):
    help = 'Simulate views/clicks/purchases for a video partner\'s courses, then close the month'

    def add_arguments(self, parser):
        parser.add_argument('--partner-email', type=str, default=None, help='Only seed this partner (default: all)')
        parser.add_argument('--year', type=int, default=None)
        parser.add_argument('--month', type=int, default=None)
        parser.add_argument('--views-min', type=int, default=25)
        parser.add_argument('--views-max', type=int, default=60)
        parser.add_argument('--purchases-min', type=int, default=2)
        parser.add_argument('--purchases-max', type=int, default=5)
        parser.add_argument('--no-close', action='store_true', help="Don't close the period after seeding")

    def handle(self, *args, **options):
        from apps.accounts.models import User
        from apps.core.constants import Roles
        from apps.courses.models import Course

        today = timezone.now().date()
        year = options['year'] or today.year
        month = options['month'] or today.month

        if options['partner_email']:
            try:
                partners = [User.objects.get(email=options['partner_email'])]
            except User.DoesNotExist:
                raise CommandError(f"Aucun utilisateur avec l'email {options['partner_email']}")
        else:
            partners = list(User.objects.filter(role=Roles.PARTNER, is_active=True))

        if not partners:
            raise CommandError('Aucun partenaire trouvé. Lancez d\'abord `python manage.py seed_partners`.')

        viewers = self._ensure_viewers()

        with transaction.atomic():
            for partner in partners:
                courses = list(Course.objects.filter(
                    revenue_partner=partner, revenue_share_rate__isnull=False,
                ))
                if not courses:
                    self.stdout.write(self.style.WARNING(
                        f'[!] {partner.get_full_name()} ({partner.email}) — aucun cours lié, ignoré'
                    ))
                    continue

                self.stdout.write(f'[+] {partner.get_full_name()} — {len(courses)} cours')
                for course in courses:
                    self._seed_course(course, viewers, year, month, options)

            self._maybe_seed_subscription(year, month)

        if not options['no_close']:
            from apps.revenue_share.services import compute_period
            results = compute_period(year, month)
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(f'Mois {month:02d}/{year} clôturé — {len(results)} ligne(s) de gain :'))
            for earning in results:
                self.stdout.write(
                    f'  - {earning.course.title}: {earning.total_revenue}{earning.currency} '
                    f'(vues={earning.view_count}, clics={earning.click_count}) '
                    f'-> {earning.earning_amount}{earning.currency} pour {earning.partner}'
                )
        else:
            self.stdout.write(self.style.SUCCESS('Données générées (mois non clôturé — utilisez close_partner_earnings_period ou l\'admin).'))

    # ─────────────────────────────────────────────────────────────────────────

    def _ensure_viewers(self):
        from apps.accounts.models import User
        from apps.core.constants import Roles

        viewers = []
        created_count = 0
        for first, last in VIEWER_NAMES:
            email = f"{_slugify(first)}.{_slugify(last)}@exemple.com"
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first, 'last_name': last,
                    'role': Roles.STUDENT, 'company': None, 'is_active': True,
                },
            )
            if created:
                user.set_password('viewer123!')
                user.save(update_fields=['password'])
                created_count += 1
            viewers.append(user)
        self.stdout.write(f'[+] Viewers de test: {len(viewers)} ({created_count} créés)')
        return viewers

    def _random_timestamp(self, year, month):
        """A random moment inside the target month, never later than now (so a same-month
        seed lands between day 1 and today; a past month gets spread across the full month)."""
        tz = timezone.get_current_timezone()
        start = timezone.make_aware(datetime(year, month, 1), tz)
        now = timezone.now()
        window_end = now if (now.year, now.month) == (year, month) else start + timedelta(days=27)
        if window_end <= start:
            window_end = start + timedelta(hours=1)
        delta_seconds = int((window_end - start).total_seconds())
        return start + timedelta(seconds=random.randint(0, max(delta_seconds, 1)))

    def _seed_course(self, course, viewers, year, month, options):
        from apps.progression.models import XAPIStatement
        from apps.courses.models import Lesson
        from apps.payments.models import Order, OrderItem

        n_views = random.randint(options['views_min'], options['views_max'])
        view_count = 0
        for _ in range(n_views):
            viewer = random.choice(viewers)
            ts = self._random_timestamp(year, month)
            stmt = XAPIStatement.objects.create(
                user=viewer, verb='experienced', object_type='course', object_id=str(course.id),
                result={'verb_detail': 'view'},
            )
            XAPIStatement.objects.filter(pk=stmt.pk).update(timestamp=ts)
            view_count += 1

        lessons = list(Lesson.objects.filter(chapter__section__course=course))
        click_count = 0
        if lessons:
            n_clicks = random.randint(int(n_views * 0.4), int(n_views * 0.8) + 1)
            for _ in range(n_clicks):
                viewer = random.choice(viewers)
                lesson = random.choice(lessons)
                ts = self._random_timestamp(year, month)
                stmt = XAPIStatement.objects.create(
                    user=viewer, verb='experienced', object_type='lesson', object_id=str(lesson.id),
                    result={'verb_detail': random.choice(['play', 'resume'])},
                )
                XAPIStatement.objects.filter(pk=stmt.pk).update(timestamp=ts)
                click_count += 1

        purchase_count = 0
        if course.price and Decimal(course.price) > 0:
            n_purchases = random.randint(options['purchases_min'], options['purchases_max'])
            buyers = random.sample(viewers, min(n_purchases, len(viewers)))
            for buyer in buyers:
                ts = self._random_timestamp(year, month)
                order = Order.objects.create(
                    user=buyer, order_type=Order.TYPE_COURSE_PURCHASE, status=Order.STATUS_PAID,
                    subtotal=course.price, total_amount=course.price, currency='XOF', paid_at=ts,
                )
                OrderItem.objects.create(
                    order=order, course=course, title_snapshot=course.title, unit_price=course.price,
                )
                purchase_count += 1

        self.stdout.write(
            f'    "{course.title}": {view_count} vues, {click_count} clics, {purchase_count} achat(s)'
        )

    def _maybe_seed_subscription(self, year, month):
        from apps.tenants.models import SubscriptionPlan
        from apps.payments.models import Order, OrderItem
        from apps.accounts.models import User
        from apps.core.constants import Roles

        plan = SubscriptionPlan.objects.first()
        if not plan or not plan.price or Decimal(plan.price) <= 0:
            self.stdout.write('[i] Aucun plan d\'abonnement payant trouvé — pool d\'abonnement non simulé')
            return

        subscriber = User.objects.filter(role=Roles.STUDENT, is_active=True).order_by('?').first()
        if not subscriber:
            return

        ts = self._random_timestamp(year, month)
        order = Order.objects.create(
            user=subscriber, order_type=Order.TYPE_SUBSCRIPTION, status=Order.STATUS_PAID,
            subscription_plan=plan, subtotal=plan.price, total_amount=plan.price,
            currency='XOF', paid_at=ts,
        )
        OrderItem.objects.create(order=order, title_snapshot=plan.name, unit_price=plan.price)
        self.stdout.write(f'[+] Abonnement simulé: {plan.name} — {plan.price} XOF (réparti selon l\'engagement du mois)')
