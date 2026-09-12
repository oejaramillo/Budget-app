from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.accounts.models import Account
from apps.currencies.models import Currency


class Holding(models.Model):
    """One position in an instrument (stock, ETF, fund, crypto, ...).

    Quantities and prices are Decimals. `quantity` needs more precision than money
    because fractional shares and crypto amounts are common.
    """

    class Kind(models.TextChoices):
        STOCK = "stock", "Stock"
        ETF = "etf", "ETF"
        FUND = "fund", "Mutual fund"
        BOND = "bond", "Bond"
        CRYPTO = "crypto", "Crypto"
        REAL_ESTATE = "real_estate", "Real estate"
        OTHER = "other", "Other"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="holdings"
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="holdings",
        help_text="Optional: the account this position is held in.",
    )
    symbol = models.CharField(max_length=32)
    name = models.CharField(max_length=200, blank=True, default="")
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.STOCK)
    quantity = models.DecimalField(
        max_digits=28,
        decimal_places=10,
        validators=[MinValueValidator(Decimal("0"))],
    )
    cost_basis = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Total amount paid for the position, fees included.",
    )
    currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, related_name="holdings"
    )
    opened_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["symbol"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "symbol", "account"], name="unique_holding_per_account"
            )
        ]

    def __str__(self) -> str:
        return f"{self.symbol} x {self.quantity}"

    @property
    def latest_valuation(self):
        """Most recent recorded valuation, or None when never valued."""
        return self.valuations.order_by("-valued_on").first()

    @property
    def market_value(self) -> Decimal:
        valuation = self.latest_valuation
        return valuation.value if valuation else self.cost_basis

    @property
    def unrealised_gain(self) -> Decimal:
        return self.market_value - self.cost_basis

    @property
    def unrealised_gain_percent(self) -> Decimal:
        if not self.cost_basis:
            return Decimal("0.00")
        return ((self.unrealised_gain / self.cost_basis) * 100).quantize(Decimal("0.01"))


class Valuation(models.Model):
    """Point-in-time value of a holding, used to build portfolio history."""

    holding = models.ForeignKey(
        Holding, on_delete=models.CASCADE, related_name="valuations"
    )
    valued_on = models.DateField()
    value = models.DecimalField(max_digits=20, decimal_places=2)
    note = models.CharField(max_length=200, blank=True, default="")
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-valued_on"]
        constraints = [
            models.UniqueConstraint(
                fields=["holding", "valued_on"], name="unique_valuation_per_day"
            )
        ]

    def __str__(self) -> str:
        return f"{self.holding.symbol} @ {self.valued_on}: {self.value}"
