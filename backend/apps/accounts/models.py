from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.currencies.models import Currency


class Account(models.Model):
    """A wallet, bank account, card or brokerage account owned by one user.

    `balance` is the *current* balance and is only changed by an explicit update
    or by applying transactions through `Account.apply_transaction`. It is a
    Decimal at all times: floats are never used for money anywhere in the app.
    """

    class Type(models.TextChoices):
        CHECKING = "checking", "Checking"
        SAVINGS = "savings", "Savings"
        CREDIT = "credit", "Credit card"
        CASH = "cash", "Cash"
        INVESTMENT = "investment", "Investment"
        LOAN = "loan", "Loan"
        OTHER = "other", "Other"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="accounts",
    )
    name = models.CharField(max_length=100)
    account_type = models.CharField(
        max_length=16, choices=Type.choices, default=Type.CHECKING
    )
    balance = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("-999999999999999999.99"))],
    )
    currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, related_name="accounts"
    )
    institution = models.CharField(max_length=200, blank=True, default="")
    official_number = models.CharField(max_length=100, blank=True, default="")
    is_active = models.BooleanField(
        default=True, help_text="Inactive accounts are hidden but keep their history."
    )
    created_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"], name="unique_account_name_per_user"
            )
        ]
        indexes = [models.Index(fields=["user", "is_active"])]

    def __str__(self) -> str:
        return f"{self.name} ({self.currency.code})"

    # -- Money helpers -------------------------------------------------------

    def apply_transaction(self, transaction) -> None:
        """Apply the signed effect of a transaction to this account balance."""
        delta = transaction.signed_amount
        Account.objects.filter(pk=self.pk).update(balance=models.F("balance") + delta)
        self.refresh_from_db(fields=["balance"])
