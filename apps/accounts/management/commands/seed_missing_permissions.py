"""
Management command: seed_missing_permissions

Adds PermissionCode entries for modules that exist in the sidebar but were never
part of the Droits & Permissions matrix (Assistant IA, Certificats, Communauté,
Paiements, Parcours, Demandes formation), and grants them by default to the same
roles that already see those modules today (per constants/modules.js on the
frontend) — so enabling enforcement doesn't lock anyone out on deploy. The admin
can then uncheck what they don't want from the matrix, same as for Sessions.

Usage:
    python manage.py seed_missing_permissions
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Add PermissionCode entries for AI/Certificates/Social/Payments/LearningPaths/TrainingRequests'

    def handle(self, *args, **options):
        from apps.accounts.models import PermissionCode, RolePermission
        from apps.core.constants import Roles

        ALL_NON_SUPER = [
            Roles.COMPANY_ADMIN, Roles.TRAINING_CENTER_ADMIN, Roles.HR,
            Roles.MANAGER, Roles.EMPLOYEE, Roles.TRAINER, Roles.STUDENT,
        ]
        TRAINING_REQUESTS_ROLES = [Roles.COMPANY_ADMIN, Roles.TRAINING_CENTER_ADMIN, Roles.HR, Roles.MANAGER, Roles.EMPLOYEE]

        PERMISSIONS = [
            # (code, label, category, default_roles)
            ('ai.use',               'Utiliser l\'assistant IA',        'Intelligence Artificielle', ALL_NON_SUPER),
            ('certificate.view',     'Voir les certificats',            'Certificats',                ALL_NON_SUPER),
            ('social.view',          'Voir la communauté',              'Communauté',                 ALL_NON_SUPER),
            ('payment.view',         'Voir les paiements',              'Paiements',                  ALL_NON_SUPER),
            ('learning_path.view',   'Voir les parcours',               'Parcours',                   ALL_NON_SUPER),
            ('training_request.view', 'Voir les demandes de formation', 'Demandes formation',         TRAINING_REQUESTS_ROLES),
        ]

        perm_count = 0
        grant_count = 0
        for code, label, category, default_roles in PERMISSIONS:
            perm, created = PermissionCode.objects.get_or_create(
                code=code, defaults={'label': label, 'category': category},
            )
            perm_count += 1 if created else 0
            for role in default_roles:
                _, granted = RolePermission.objects.get_or_create(role=role, permission=perm)
                grant_count += 1 if granted else 0

        self.stdout.write(self.style.SUCCESS(
            f'  {perm_count} new PermissionCode(s), {grant_count} new RolePermission grant(s)'
        ))
