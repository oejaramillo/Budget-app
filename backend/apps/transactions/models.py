from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q

from apps.accounts.models import Account
from apps.currencies.models import Currency


class Category(models.Model):
    """A user-defined label for transactions, optionally tied to a budget."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="categories"
    )
    name = models.CharField(max_length=100)
    budget = models.ForeignKey(
        "budgets.Budget",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="categories",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"], name="unique_category_name_per_user"
            )
        ]

    def __str__(self) -> str:
        return self.name


class Transaction(models.Model):
    """A single money movement on one account.

    Rules enforced at the database level as well as in the serializer and the
    service layer:

    * `amount` is always a positive Decimal; direction comes from `kind`.
    * income/expense must reference a category-free or category-optional account
      owned by the same user (checked in `services`).
    * a transfer must name a `destination_account`; the amount is subtracted from
      `account` and added to `destination_account`.
    * `currency` defaults to the account currency. A different currency is only
      accepted together with an explicit `exchange_rate`, which keeps conversion
      arithmetic auditable instead of implicit.
    """

    class Type(models.TextChoices):
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"
        TRANSFER = "transfer", "Transfer"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions"
    )
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="transactions"
    )
    destination_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incoming_transfers",
        help_text="Required for transfers: the account receiving the money.",
    )
    transaction_type = models.CharField(max_length=10, choices=Type.choices)
    transaction_date = models.DateField()
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Always positive. Direction is derived from transaction_type.",
    )
    currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, related_name="transactions"
    )
    exchange_rate = models.DecimalField(
        max_digits=24,
        decimal_places=12,
        null=True,
        blank=True,
        help_text="Only for transactions in a currency other than the account's.",
    )
    description = models.TextField(blank=True, default="")
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    budget = models.ForeignKey(
        "budgets.Budget",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-transaction_date", "-created_date"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0), name="transaction_amount_positive"
            ),
            models.CheckConstraint(
                condition=(
                    Q(transaction_type="transfer", destination_account__isnull=False)
                    | ~Q(transaction_type="transfer")
                ),
                name="transfer_requires_destination",
            ),
            models.CheckConstraint(
                condition=(
                    Q(destination_account__isnull=True)
                    | ~Q(account=F("destination_account"))
                ),
                name="transfer_accounts_must_differ",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "transaction_date"]),
            models.Index(fields=["account", "transaction_date"]),
            models.Index(fields=["user", "transaction_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_transaction_type_display()} {self.amount} ({self.account})"

    @property
    def signed_amount(self) -> Decimal:
        """Effect of this transaction on `account`."""
        if self.transaction_type == self.Type.EXPENSE:
            return -Decimal(self.amount)
        if self.transaction_type == self.Type.TRANSFER:
            return -Decimal(self.amount)
        return Decimal(self.amount)
