from django.core.management.base import BaseCommand

from apps.tenants.models import SubscriptionPlan


PLANS = [
    {
        'name': 'Mensuel',
        'code': 'b2c-monthly',
        'plan_type': SubscriptionPlan.PLAN_TYPE_B2C,
        'billing_cycle': SubscriptionPlan.BILLING_MONTHLY,
        'price': 5000,
        'currency': 'XOF',
        'features': {
            'badge': None,
            'tagline': 'Idéal pour découvrir',
            'items': [
                'Accès à tout le catalogue',
                'Suivi de progression',
                'Exercices & quiz',
                'Support communautaire',
            ],
        },
    },
    {
        'name': 'Trimestriel',
        'code': 'b2c-quarterly',
        'plan_type': SubscriptionPlan.PLAN_TYPE_B2C,
        'billing_cycle': SubscriptionPlan.BILLING_QUARTERLY,
        'price': 13500,
        'currency': 'XOF',
        'features': {
            'badge': 'Populaire',
            'tagline': 'Économisez 10 %',
            'items': [
                'Accès à tout le catalogue',
                'Suivi de progression',
                'Exercices & quiz',
                'Certificats de complétion',
                'Support prioritaire',
            ],
        },
    },
    {
        'name': 'Semestriel',
        'code': 'b2c-semi-annual',
        'plan_type': SubscriptionPlan.PLAN_TYPE_B2C,
        'billing_cycle': SubscriptionPlan.BILLING_SEMI_ANNUAL,
        'price': 24000,
        'currency': 'XOF',
        'features': {
            'badge': None,
            'tagline': 'Économisez 20 %',
            'items': [
                'Accès à tout le catalogue',
                'Suivi de progression',
                'Exercices & quiz',
                'Certificats de complétion',
                'Téléchargement des ressources',
                'Support prioritaire',
            ],
        },
    },
    {
        'name': 'Annuel',
        'code': 'b2c-yearly',
        'plan_type': SubscriptionPlan.PLAN_TYPE_B2C,
        'billing_cycle': SubscriptionPlan.BILLING_YEARLY,
        'price': 42000,
        'currency': 'XOF',
        'features': {
            'badge': 'Meilleure valeur',
            'tagline': 'Économisez 30 %',
            'items': [
                'Accès à tout le catalogue',
                'Suivi de progression',
                'Exercices & quiz',
                'Certificats de complétion',
                'Téléchargement des ressources',
                'Accès aux classes virtuelles',
                'Support VIP 24/7',
            ],
        },
    },
]


class Command(BaseCommand):
    help = 'Create default B2C subscription plans for the training centre'

    def handle(self, *args, **options):
        created = updated = 0
        for data in PLANS:
            obj, was_created = SubscriptionPlan.objects.get_or_create(
                code=data['code'],
                defaults=data,
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'  Created: {data["name"]} ({data["price"]} {data["currency"]})'))
            else:
                # Always sync features in case they changed
                obj.features = data['features']
                obj.save(update_fields=['features'])
                updated += 1
                self.stdout.write(f'  Updated features: {data["name"]}')

        self.stdout.write(self.style.SUCCESS(f'\nDone — {created} created, {updated} updated.'))
