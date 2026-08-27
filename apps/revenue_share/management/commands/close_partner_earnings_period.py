from django.core.management.base import BaseCommand, CommandError

from apps.revenue_share.services import compute_period


class Command(BaseCommand):
    help = "Clôture un mois de partage de revenus partenaires (calcule et enregistre PartnerMonthlyEarning pour chaque cours lié)."

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, required=True)
        parser.add_argument('--month', type=int, required=True)

    def handle(self, *args, **options):
        year, month = options['year'], options['month']
        try:
            results = compute_period(year, month)
        except ValueError as exc:
            raise CommandError(str(exc))

        self.stdout.write(self.style.SUCCESS(f'{len(results)} cours clôturé(s) pour {month:02d}/{year} :'))
        for earning in results:
            self.stdout.write(
                f'  - {earning.course.title}: {earning.total_revenue}{earning.currency} '
                f'→ {earning.earning_amount}{earning.currency} pour {earning.partner}'
            )
