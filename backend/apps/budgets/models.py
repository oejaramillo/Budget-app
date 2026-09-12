from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.currencies.models import Currency


class Budget(models.Model):
    """A spending envelope for a period.

    `accounts` is the set of accounts the budget applies to. Keeping it as an
    explicit link (instead of a separate join model) removes a table and makes the
    ownership check trivial.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="budgets"
    )
    name = models.CharField(max_length=100)
    min_amount = models.DecimalField(
        max_digits=20, decimal_places=2, default=Decimal("0.00")
    )
    max_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, related_name="budgets"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    accounts = models.ManyToManyField(
        "accounts.Account", related_name="budgets", blank=True
    )
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date", "name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(max_amount__gte=models.F("min_amount")),
                name="budget_max_gte_min",
            ),
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="budget_end_after_start",
            ),
        ]
        indexes = [models.Index(fields=["user", "start_date", "end_date"])]

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        super().clean()
        if self.min_amount is not None and self.max_amount is not None:
            if self.min_amount > self.max_amount:
                raise ValidationError(
                    {"min_amount": "Minimum amount cannot be greater than the maximum amount."}
                )
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date must be on or after the start date."})

    @property
    def is_current(self) -> bool:
        from django.utils import timezone

        today = timezone.localdate()
        return self.start_date <= today <= self.end_date
