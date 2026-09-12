"""Refresh the shared currency catalogue from the exchange-rate provider.

Usage:
    python manage.py refresh_currencies                 # update existing + create new
    python manage.py refresh_currencies --no-create     # only refresh known currencies
    python manage.py refresh_currencies --base EUR       # use a different base currency
    python manage.py refresh_currencies --force          # ignore the staleness guard
    python manage.py refresh_currencies --bootstrap      # create only the base currency, no network
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.currencies.models import Currency
from apps.currencies.services import ExchangeRateError, record_failure, refresh_rates

#: Skip the provider call when rates are fresher than this, unless --force is used.
STALENESS_GUARD = timedelta(hours=6)


class Command(BaseCommand):
    help = "Fetch and store currency exchange rates from the configured provider."

    def add_arguments(self, parser):
        parser.add_argument(
            "--base",
            default=settings.BASE_CURRENCY_CODE,
            help=f"Base currency code (default: {settings.BASE_CURRENCY_CODE}).",
        )
        parser.add_argument(
            "--no-create",
            action="store_true",
            help="Do not create currencies that are missing locally.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Refresh even when rates were updated recently.",
        )
        parser.add_argument(
            "--bootstrap",
            action="store_true",
            help="Create the base currency only, without contacting the provider.",
        )

    def handle(self, *args, **options):
        base = options["base"].upper()

        if options["bootstrap"]:
            currency, created = Currency.objects.get_or_create(
                code=base,
                defaults={
                    "name": "US Dollar" if base == "USD" else base,
                    "exchange_rate": 1,
                    "principal": True,
                    "is_active": True,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created base currency {base}."))
            else:
                self.stdout.write(f"Base currency {base} already exists.")
            return

        # Cheap guard: avoid hammering the provider when nothing changed.
        if not options["force"]:
            newest = (
                Currency.objects.exclude(rate_updated_at=None)
                .order_by("-rate_updated_at")
                .values_list("rate_updated_at", flat=True)
                .first()
            )
            if newest and timezone.now() - newest < STALENESS_GUARD:
                self.stdout.write(
                    self.style.WARNING(
                        "Rates were refreshed less than 6 hours ago; use --force to refresh anyway."
                    )
                )
                return

        try:
            result = refresh_rates(base_code=base, create_missing=not options["no_create"])
        except ExchangeRateError as exc:
            record_failure("exchangerate-api", base, str(exc))
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(result.message))
        if result.created:
            self.stdout.write(f"Created: {', '.join(result.created)}")
        if result.skipped:
            self.stdout.write(f"Skipped: {', '.join(result.skipped)}")
