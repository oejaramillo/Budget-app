"""Business rules for creating, updating and deleting transactions.

Keeping this out of the serializer matters because balances must stay consistent
no matter which entry point is used (API, admin, shell, data import).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from django.db import transaction as db_transaction

from apps.accounts.models import Account
from apps.budgets.models import Budget
from apps.currencies.models import Currency

from .models import Category, Transaction


class TransactionRuleError(DjangoValidationError):
    """Raised when a transaction would violate an ownership or money rule."""


def _as_decimal(value, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise TransactionRuleError({field: "A decimal number is required."}) from exc


def _resolve(user, value, model, field: str, *, required: bool = False):
    """Return an object owned by `user`, or raise.

    The error message is identical for "does not exist" and "belongs to another
    user" so the API never confirms that another tenant's row exists.
    """
    if value in (None, ""):
        if required:
            raise TransactionRuleError({field: "This field is required."})
        return None
    if isinstance(value, model):
        obj = value
    else:
        try:
            obj = model.objects.get(pk=value)
        except (model.DoesNotExist, ValueError, TypeError):
            raise TransactionRuleError(
                {field: f"Invalid {model._meta.verbose_name} for this user."}
            )
    # `Currency` is shared reference data and has no owner column; every other
    # related model must belong to the requesting user.
    if any(f.name == "user" for f in model._meta.fields):
        if obj.user_id != user.pk:
            raise TransactionRuleError(
                {field: f"Invalid {model._meta.verbose_name} for this user."}
            )
    return obj


def validate_transaction_payload(
    user, data: dict, *, instance: Transaction | None = None
) -> dict:
    """Resolve related objects and enforce every transactional rule.

    `data` may contain model instances or primary keys. Missing keys fall back to
    the values already on `instance`, which is what makes partial updates safe.
    """
    data = dict(data)

    def current(field):
        if field in data:
            return data[field]
        return getattr(instance, field, None) if instance is not None else None

    account = _resolve(user, current("account"), Account, "account", required=True)
    destination = _resolve(
        user, current("destination_account"), Account, "destination_account"
    )
    category = _resolve(user, current("category"), Category, "category")
    budget = _resolve(user, current("budget"), Budget, "budget")

    kind = current("transaction_type")
    amount = current("amount")

    if amount in (None, ""):
        raise TransactionRuleError({"amount": "This field is required."})
    if _as_decimal(amount, "amount") <= 0:
        raise TransactionRuleError({"amount": "Amount must be greater than zero."})

    if kind == Transaction.Type.TRANSFER:
        if destination is None:
            raise TransactionRuleError(
                {"destination_account": "A transfer requires a destination account."}
            )
        if destination.pk == account.pk:
            raise TransactionRuleError(
                {"destination_account": "Source and destination accounts must differ."}
            )
        if category is not None:
            raise TransactionRuleError({"category": "Transfers cannot be categorised."})
        if budget is not None:
            raise TransactionRuleError({"budget": "Transfers cannot belong to a budget."})
    else:
        if kind not in Transaction.Type.values:
            raise TransactionRuleError({"transaction_type": "Invalid transaction type."})
        if destination is not None:
            raise TransactionRuleError(
                {"destination_account": "Only transfers may have a destination account."}
            )

    if category is not None and budget is not None:
        if category.budget_id not in (None, budget.pk):
            raise TransactionRuleError(
                {"budget": "The chosen category belongs to a different budget."}
            )

    # Currency: default to the account currency. A foreign currency is allowed
    # only together with an explicit rate, so conversions stay auditable.
    currency = _resolve(user, current("currency"), Currency, "currency")
    rate = current("exchange_rate")

    if currency is None:
        data["currency"] = account.currency
    elif currency.pk != account.currency_id:
        if rate in (None, ""):
            raise TransactionRuleError(
                {
                    "exchange_rate": (
                        "Provide an explicit exchange rate when the transaction "
                        "currency differs from the account currency."
                    )
                }
            )
        if _as_decimal(rate, "exchange_rate") <= 0:
            raise TransactionRuleError({"exchange_rate": "Exchange rate must be positive."})
    else:
        data["exchange_rate"] = None

    # Normalise to instances so the caller can persist without re-resolving.
    data.update(
        account=account,
        destination_account=destination,
        category=category,
        budget=budget,
    )
    return data


@db_transaction.atomic
def create_transaction(user, data: dict) -> Transaction:
    cleaned = validate_transaction_payload(user, data)
    transaction = Transaction.objects.create(user=user, **cleaned)
    _apply_balance(transaction, direction=1)
    return transaction


@db_transaction.atomic
def update_transaction(instance: Transaction, data: dict) -> Transaction:
    # Validate first: if the new values are rejected, nothing has been touched.
    cleaned = validate_transaction_payload(instance.user, data, instance=instance)
    # Revert the old effect, persist the new values, then apply the new effect.
    _apply_balance(instance, direction=-1)
    for field, value in cleaned.items():
        setattr(instance, field, value)
    instance.save()
    instance.refresh_from_db()
    _apply_balance(instance, direction=1)
    return instance


@db_transaction.atomic
def delete_transaction(instance: Transaction) -> None:
    _apply_balance(instance, direction=-1)
    instance.delete()


def _apply_balance(transaction: Transaction, *, direction: int) -> None:
    """Move money on the affected accounts. `direction` is +1 apply, -1 revert."""
    delta = transaction.signed_amount * direction
    Account.objects.filter(pk=transaction.account_id).update(
        balance=models.F("balance") + delta
    )
    if (
        transaction.transaction_type == Transaction.Type.TRANSFER
        and transaction.destination_account_id
    ):
        Account.objects.filter(pk=transaction.destination_account_id).update(
            balance=models.F("balance") - delta
        )
    for account in (transaction.account, transaction.destination_account):
        if account is not None:
            account.refresh_from_db(fields=["balance"])
