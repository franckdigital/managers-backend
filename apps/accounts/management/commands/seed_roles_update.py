"""
Management command: seed_roles_update
Adds:
  - RoleDefinition for training_center_admin ("Admin Centre de Formation")
  - PermissionCode entries for "Apprenants B2C" category
  - Default role-permission grants for training_center_admin
  - Updates training_center_admin@lmspro.com user's role

Usage:
    python manage.py seed_roles_update
"""
from django.core.management.base import BaseCommand
from apps.core.constants import Roles


class Command(BaseCommand):
    help = 'Add training_center_admin role and B2C learner permissions to the matrix'

    def handle(self, *args, **options):
        from apps.accounts.models import PermissionCode, RoleDefinition, RolePermission, User

        # ── 1. RoleDefinition for training_center_admin ───────────────────────
        self.stdout.write('[1] RoleDefinitions…')
        tc_role, created = RoleDefinition.objects.get_or_create(
            key=Roles.TRAINING_CENTER_ADMIN,
            defaults={
                'label': 'Admin Centre de Formation',
                'color': 'teal',
                'is_system': True,
            },
        )
        if not created:
            # Ensure label and color are up to date
            tc_role.label = 'Admin Centre de Formation'
            tc_role.color = 'teal'
            tc_role.is_system = True
            tc_role.save(update_fields=['label', 'color', 'is_system'])
        self.stdout.write(self.style.SUCCESS(f'  [{"+" if created else "="}] {tc_role.label} ({tc_role.key})'))

        # ── 2. B2C Learner permission codes ───────────────────────────────────
        self.stdout.write('[2] Apprenants B2C permissions…')
        B2C_PERMISSIONS = [
            ('b2c.subscribe',          'Souscrire un abonnement B2C',          'Apprenants B2C'),
            ('b2c.view_catalog',       'Voir le catalogue de formations B2C',  'Apprenants B2C'),
            ('b2c.access_tc',          'Accéder au centre de formation',       'Apprenants B2C'),
            ('b2c.view_certificates',  'Voir ses certificats B2C',             'Apprenants B2C'),
            ('b2c.manage_learners',    'Gérer les apprenants B2C (admin)',     'Apprenants B2C'),
            ('b2c.view_stats',         'Voir les statistiques apprenants B2C', 'Apprenants B2C'),
        ]
        for code, label, category in B2C_PERMISSIONS:
            perm, created = PermissionCode.objects.get_or_create(
                code=code, defaults={'label': label, 'category': category},
            )
            self.stdout.write(f'  [{"+" if created else "="}] {perm.label}')

        # ── 3. TC admin permissions (same as company_admin + B2C perms) ───────
        self.stdout.write('[3] Granting permissions to training_center_admin…')

        # Give TC admin: all non-admin.manage_roles permissions + all B2C perms
        all_perms = list(PermissionCode.objects.all())
        tc_admin_perms = [
            p for p in all_perms
            if not p.code.startswith('admin.manage_roles')
        ]
        count = 0
        for perm in tc_admin_perms:
            _, created = RolePermission.objects.get_or_create(
                role=Roles.TRAINING_CENTER_ADMIN, permission=perm,
            )
            if created:
                count += 1
        self.stdout.write(self.style.SUCCESS(f'  {count} new permission(s) granted'))

        # Also grant company_admin the new B2C management permissions
        self.stdout.write('[4] Granting B2C manage perms to company_admin…')
        count_ca = 0
        for code, _, _ in B2C_PERMISSIONS:
            try:
                perm = PermissionCode.objects.get(code=code)
                _, created = RolePermission.objects.get_or_create(
                    role=Roles.COMPANY_ADMIN, permission=perm,
                )
                if created:
                    count_ca += 1
            except PermissionCode.DoesNotExist:
                pass
        self.stdout.write(self.style.SUCCESS(f'  {count_ca} new permission(s) granted to company_admin'))

        # Grant students the B2C learner-facing permissions
        self.stdout.write('[5] Granting B2C learner perms to student role…')
        STUDENT_B2C = ['b2c.subscribe', 'b2c.view_catalog', 'b2c.access_tc', 'b2c.view_certificates']
        count_st = 0
        for code in STUDENT_B2C:
            try:
                perm = PermissionCode.objects.get(code=code)
                _, created = RolePermission.objects.get_or_create(
                    role=Roles.STUDENT, permission=perm,
                )
                if created:
                    count_st += 1
            except PermissionCode.DoesNotExist:
                pass
        self.stdout.write(self.style.SUCCESS(f'  {count_st} new permission(s) granted to student'))

        # ── 4. Update TC admin user's role ────────────────────────────────────
        self.stdout.write('[6] Updating training_center_admin user role…')
        updated = User.objects.filter(email='training_center_admin@lmspro.com').update(
            role=Roles.TRAINING_CENTER_ADMIN
        )
        if updated:
            self.stdout.write(self.style.SUCCESS(f'  Updated {updated} user(s) to training_center_admin'))
        else:
            self.stdout.write('  training_center_admin@lmspro.com not found (skipped)')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('  seed_roles_update completed!'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
