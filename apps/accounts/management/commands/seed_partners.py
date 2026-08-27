"""
Management command: seed_partners
Creates test video partners (role=PARTNER) — some at 30%, some at 40% — and links
each of them to 1-2 existing published courses (revenue_partner + revenue_share_rate)
so the revenue-share feature can be tested end-to-end right away.

Usage:
    python manage.py seed_partners
    python manage.py seed_partners --reset
"""
from django.core.management.base import BaseCommand
from django.db import transaction

PARTNERS = [
    ('Karim',     'Ndiaye',    30),
    ('Aïcha',     'Camara',    30),
    ('Bakary',    'Cissé',     40),
    ('Solange',   'Yao',       40),
]

COURSES_PER_PARTNER = 2


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
    help = 'Create test video partners (role=PARTNER) and link them to a few published courses'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Remove existing test partners before seeding')

    def handle(self, *args, **options):
        if options['reset']:
            self._reset()

        with transaction.atomic():
            partners = self._create_partners()
            self._link_courses(partners)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('  seed_partners completed!'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write('Login with any partner email below, password: partner123!')
        for first, last, rate in PARTNERS:
            email = f"{_slugify(first)}.{_slugify(last)}@exemple.com"
            self.stdout.write(f'  - {email}  ({rate}%)')

    def _reset(self):
        from apps.accounts.models import User
        emails = [f"{_slugify(first)}.{_slugify(last)}@exemple.com" for first, last, _ in PARTNERS]
        self.stdout.write('Removing existing test partners...')
        # Unlink any course pointing at these users before deleting them (SET_NULL handles
        # this automatically on delete, but we clear explicitly for clarity in the logs).
        from apps.courses.models import Course
        Course.objects.filter(revenue_partner__email__in=emails).update(
            revenue_partner=None, revenue_share_rate=None,
        )
        count, _ = User.objects.filter(email__in=emails).delete()
        self.stdout.write(f'  Removed {count} records')

    def _create_partners(self):
        from apps.accounts.models import User
        from apps.core.constants import Roles

        partners = []
        created_count = 0
        for first, last, rate in PARTNERS:
            email = f"{_slugify(first)}.{_slugify(last)}@exemple.com"
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'role': Roles.PARTNER,
                    'company': None,
                    'is_active': True,
                    'partner_default_rate': rate,
                    'payout_method': 'bank_transfer',
                    'bank_account_name': f'{first} {last}',
                    'bank_iban': 'CI93CI0080000000000000000001',
                },
            )
            if created:
                user.set_password('partner123!')
                user.save(update_fields=['password'])
                created_count += 1
            elif user.role != Roles.PARTNER or user.partner_default_rate != rate:
                user.role = Roles.PARTNER
                user.partner_default_rate = rate
                user.save(update_fields=['role', 'partner_default_rate'])
            partners.append((user, rate))

        self.stdout.write(f'[+] Partners: {len(partners)} ({created_count} created)')
        return partners

    def _link_courses(self, partners):
        from apps.courses.models import Course

        available = list(Course.objects.filter(
            status=Course.STATUS_PUBLISHED, revenue_partner__isnull=True,
        ))
        linked = 0
        idx = 0
        for user, rate in partners:
            for _ in range(COURSES_PER_PARTNER):
                if idx >= len(available):
                    break
                course = available[idx]
                idx += 1
                course.revenue_partner = user
                course.revenue_share_rate = rate
                course.save(update_fields=['revenue_partner', 'revenue_share_rate'])
                linked += 1
                self.stdout.write(f'    linked "{course.title}" -> {user.get_full_name()} ({rate}%)')

        if not available:
            self.stdout.write('[!] No unlinked published courses found — partners created without course links')
        self.stdout.write(f'[+] Courses linked: {linked}')
