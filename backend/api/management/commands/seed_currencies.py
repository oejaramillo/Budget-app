from django.core.management.base import BaseCommand
from api.models import Currencies
from django.conf import settings
import requests
from decimal import Decimal

API_KEY = settings.EXCHANGE_API_KEY
BASE_URL = f"https://v6.exchangerate-api.com/v6/{API_KEY}/latest/USD"

class Command(BaseCommand):
    help = "Seed initial currencies and exchange rates with USD as principal currency"

    def handle(self, *args, **options):
        if Currencies.objects.exists():
            self.stdout.write(self.style.WARNING("Currencies already exist. Aborting."))
            return

        self.stdout.write(f"Fetching currency rates from {BASE_URL}...")
        response = requests.get(BASE_URL)
        if response.status_code != 200:
            self.stdout.write(self.style.ERROR(f"API error: {response.text}"))
            return

        data = response.json()
        rates = data.get("conversion_rates", {})
        if not rates:
            self.stdout.write(self.style.ERROR("No rates found in API response."))
            return

        usd_currency = Currencies.objects.create(
            name="US Dollar",
            code="USD",
            exchange_rate=Decimal("1.0"),
            principal=True,
            is_active=True
        )
        self.stdout.write(self.style.SUCCESS("Created USD as principal currency."))

        created = 0
        for code, rate in rates.items():
            if code == "USD":
                continue

            Currencies.objects.create(
                name=code,
                code=code,
                exchange_rate=Decimal(str(rate)),
                principal=False,
                is_active=True
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Created {created} currencies successfully."))
