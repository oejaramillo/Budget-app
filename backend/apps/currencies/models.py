from decimal import Decimal, InvalidOperation
from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Currency(models.Model):
    """A currency known to the application together with its reference rate.

    `exchange_rate` is stored as *units of this currency per one unit of the base
    currency* (`settings.BASE_CURRENCY_CODE`, USD by default). The base currency
    therefore always has a rate of exactly 1.

    The catalogue is global rather than per user: currencies and their rates are
    reference data shared by every tenant. Rates are refreshed by the
    `refresh_currencies` management command or by a staff user through the API.
    """

    code = models.CharField(
        max_length=3,
        unique=True,
        help_text="ISO 4217 code, for example 'EUR'. Stored uppercase.",
    )
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=8, blank=True)
    exchange_rate = models.DecimalField(
        max_digits=24,
        decimal_places=12,
        validators=[MinValueValidator(Decimal("0.000000000001"))],
        help_text="Units of this currency per 1 unit of the base currency.",
    )
    principal = models.BooleanField(
        default=False,
        help_text="The app-wide reporting currency. Exactly one currency has this set.",
    )
    is_active = models.BooleanField(default=True)
    rate_updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["code"]
        verbose_name_plural = "currencies"
        constraints = [
            models.UniqueConstraint(
                fields=["principal"],
                condition=models.Q(principal=True),
                name="unique_principal_currency",
            ),
            models.CheckConstraint(
                condition=models.Q(exchange_rate__gt=0),
                name="currency_exchange_rate_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"

    def clean(self) -> None:
        super().clean()
        self.code = self.normalise_code(self.code)

    @staticmethod
    def normalise_code(code: str) -> str:
        return (code or "").strip().upper()

    def save(self, *args, **kwargs):
        self.code = self.normalise_code(self.code)
        if self.rate_updated_at is None:
            self.rate_updated_at = timezone.now()
        super().save(*args, **kwargs)

    # -- Conversion helpers --------------------------------------------------

    def convert_to(self, amount: Decimal, target: "Currency") -> Decimal:
        """Convert `amount` from this currency into `target` currency.

        Rates are both expressed against the base currency, so a direct cross
        rate is enough and no extra network call is needed.
        """
        if not isinstance(amount, Decimal):
            raise TypeError("amount must be a Decimal, never a float.")
        if self.pk == target.pk:
            return amount
        rate = Decimal(target.exchange_rate) / Decimal(self.exchange_rate)
        return (amount * rate).quantize(Decimal("0.01"))

    @classmethod
    def principal_currency(cls) -> Optional["Currency"]:
        """Return the app-wide reporting currency, if one is configured."""
        return cls.objects.filter(principal=True, is_active=True).first()

    @classmethod
    def base_currency(cls) -> Optional["Currency"]:
        return cls.objects.filter(code=settings.BASE_CURRENCY_CODE).first()


class ExchangeRateSnapshot(models.Model):
    """Audit trail of rate refreshes.

    Keeps the previous value of every rate so a bad provider response can be
    spotted and rolled back without guessing.
    """

    fetched_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=64, default="exchangerate-api")
    base_code = models.CharField(max_length=3)
    updated_count = models.PositiveIntegerField(default=0)
    created_count = models.PositiveIntegerField(default=0)
    succeeded = models.BooleanField(default=True)
    message = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-fetched_at"]

    def __str__(self) -> str:
        state = "ok" if self.succeeded else "failed"
        return f"{self.fetched_at:%Y-%m-%d %H:%M} {self.base_code} ({state})"


class ExchangeRateHistory(models.Model):
    """Value of one currency rate at the time a snapshot was taken."""

    snapshot = models.ForeignKey(
        ExchangeRateSnapshot, on_delete=models.CASCADE, related_name="rates"
    )
    currency = models.ForeignKey(
        Currency, on_delete=models.CASCADE, related_name="rate_history"
    )
    rate = models.DecimalField(max_digits=24, decimal_places=12)

    class Meta:
        ordering = ["-snapshot__fetched_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["snapshot", "currency"], name="unique_rate_per_snapshot"
            )
        ]

    def __str__(self) -> str:
        return f"{self.currency.code} = {self.rate}"


def decimal_or_none(value) -> Optional[Decimal]:
    """Best-effort Decimal conversion used when reading provider payloads."""
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:  # pragma: no cover
        raise ValidationError(f"'{value}' is not a valid decimal number.") from exc
