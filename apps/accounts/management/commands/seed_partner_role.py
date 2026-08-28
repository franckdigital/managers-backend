"""
Management command: seed_partner_role
Registers the "partner" (Partenaire vidéo) role as a RoleDefinition row, so it appears
in the "Créer un utilisateur" role dropdown and the Droits & Permissions role list —
adding Roles.PARTNER to apps.core.constants alone does not do this, RoleDefinition is
a separate DB table (see seed_roles_update.py for the training_center_admin precedent).

Usage:
    python manage.py seed_partner_role
"""
from django.core.management.base import BaseCommand

from apps.core.constants import Roles


class Command(BaseCommand):
    help = 'Register the PARTNER role as a RoleDefinition so it shows up in the user-creation UI'

    def handle(self, *args, **options):
        from apps.accounts.models import RoleDefinition

        role, created = RoleDefinition.objects.get_or_create(
            key=Roles.PARTNER,
            defaults={'label': 'Partenaire vidéo', 'color': 'pink', 'is_system': True},
        )
        if not created:
            role.label = 'Partenaire vidéo'
            role.color = 'pink'
            role.is_system = True
            role.save(update_fields=['label', 'color', 'is_system'])

        self.stdout.write(self.style.SUCCESS(
            f'[{"+" if created else "="}] {role.label} ({role.key}) enregistré comme rôle système'
        ))
