"""Import a ledger export (CSV) into accounts, categories, budgets and transactions.

Written for the real export format used by this project: a semicolon-delimited CSV
with Spanish headers.

    fecha;monto;categoría;cuenta;presupuesto;descripción;moneda;número de transacción;

Design decisions worth knowing before reading the code:

* **Parse first, write once.** `parse_csv` builds a complete, validated plan in
  memory. Nothing touches the database until `commit_plan`. A dry run is therefore
  a genuine rehearsal, not a partial write.
* **The CSV's signs become transaction types.** Negative amounts are expenses,
  positive amounts are income. `Transaction.amount` is always positive, so the sign
  is consumed here.
* **Opening balances are ordinary transactions.** The `Inicio` rows are kept as
  income entries (they *are* how the account started) and the account's final
  balance is reconciled to the CSV's closing sum afterwards, which is recorded as an
  explicit adjustment rather than by faking a transaction.
* **One account per (name, currency).** An account holding two currencies cannot be
  represented, so `Efectivo` becomes `Efectivo (USD)` and `Efectivo (ARS)`. The CSV
  makes that split natural: the non-USD rows are one contiguous period.
* **Exact re-runs are no-ops.** Every row gets a deterministic `import_key`;
  importing the same file twice creates nothing the second time.
"""

from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.db import transaction as db_transaction
from django.db.models import Sum

from apps.accounts.models import Account
from apps.budgets.models import Budget
from apps.currencies.models import Currency
from apps.transactions.models import Category, Transaction

# ---------------------------------------------------------------------------
# Source-format knowledge
# ---------------------------------------------------------------------------

#: Header names, exactly as they appear in the export.
COLUMNS = {
    "date": "fecha",
    "amount": "monto",
    "category": "categoría",
    "account": "cuenta",
    "budget": "presupuesto",
    "description": "descripción",
    "currency": "moneda",
    "reference": "número de transacción",
}

DATE_FORMAT = "%d/%m/%Y"

#: Spanish currency names -> ISO 4217 codes.
CURRENCY_CODES = {
    "dólar estadounidense": "USD",
    "pesos argentinos": "ARS",
    "pesos colombianos": "COP",
    "pesos mexicanos": "MXN",
}

#: ISO code -> (display name, symbol, rate per 1 USD when the currency is created).
#: Rates for the non-USD currencies are rough values for the period the CSV covers;
#: they only affect converted reporting, and can be refreshed at any time from the
#: Currencies tab. USD is the base currency and therefore exactly 1.
CURRENCY_DEFAULTS = {
    "USD": ("US Dollar", "$", Decimal("1")),
    "ARS": ("Argentine Peso", "$", Decimal("130")),
    "COP": ("Colombian Peso", "$", Decimal("4000")),
    "MXN": ("Mexican Peso", "$", Decimal("19")),
}

#: Account type inferred from the account name. Anything unmatched becomes "other"
#: and can be corrected in the Accounts tab.
ACCOUNT_TYPE_RULES = (
    (r"visa|diners|mastercard|amex", Account.Type.CREDIT),
    (r"ibkr|inversi|fondo|bolsa|trading", Account.Type.INVESTMENT),
    (r"efectivo|cash|billetera", Account.Type.CASH),
    (r"santander|produbanco|banco|bank|pichincha|pac[ií]fico|mercado ?pago|edu |cuenta", Account.Type.CHECKING),
)

#: Rows whose category is this are opening balances.
OPENING_CATEGORY = "Inicio"

#: Category used when the export has no category at all.
UNCATEGORISED = "Sin categoría"

#: Export category -> canonical category, for names that differ only by casing.
CATEGORY_ALIASES = {
    "ropa": "Ropa",
    "casa": "Casa",
}


class ImportError_(RuntimeError):
    """A problem with the source file that makes the import unsafe to run."""


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------


@dataclass
class Row:
    """One validated CSV row, ready to become a transaction."""

    line: int
    date: date
    amount: Decimal  # always positive
    transaction_type: str
    category: str
    account: str
    currency_code: str
    budget: str | None
    description: str
    reference: str
    import_key: str

    @property
    def signed_amount(self) -> Decimal:
        return -self.amount if self.transaction_type == Transaction.Type.EXPENSE else self.amount

    @property
    def content_signature(self) -> tuple:
        """Everything about the row except where it sits in the file.

        Used to spot rows that are repeats of one another. The import key includes
        the position, so it cannot answer that question.
        """
        return (
            self.date,
            self.amount,
            self.account,
            self.currency_code,
            self.category,
            self.description,
            self.budget or "",
        )


@dataclass
class AccountPlan:
    """An account to create, with the balances the CSV implies for it."""

    name: str
    currency_code: str
    account_type: str
    transaction_count: int = 0
    #: Sum of the account's rows, i.e. the balance the export implies.
    closing_balance: Decimal = Decimal("0.00")
    opening_balance: Decimal = Decimal("0.00")
    first_date: date | None = None
    last_date: date | None = None


@dataclass
class ImportPlan:
    rows: list[Row] = field(default_factory=list)
    accounts: dict[tuple[str, str], AccountPlan] = field(default_factory=dict)
    categories: set[str] = field(default_factory=set)
    budgets: dict[str, list[date]] = field(default_factory=dict)
    currencies: set[str] = field(default_factory=set)
    skipped: list[tuple[int, str]] = field(default_factory=list)
    warnings: list[tuple[int, str]] = field(default_factory=list)

    @property
    def total_amount(self) -> Decimal:
        return sum((row.amount for row in self.rows), Decimal("0.00"))


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

_AMOUNT_STRIP = re.compile(r"[,\s]")


def parse_amount(raw: str, line: int) -> Decimal:
    """Parse `1,234.56` / `-4,800.00` into a positive-or-negative Decimal."""
    text = (raw or "").strip()
    if not text:
        raise ImportError_(f"line {line}: amount is empty")
    cleaned = _AMOUNT_STRIP.sub("", text)
    try:
        value = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ImportError_(f"line {line}: unparseable amount {raw!r}") from exc
    if value == value.to_integral_value() and "." not in cleaned:
        value = value.quantize(Decimal("0.01"))
    return value


def parse_date(raw: str, line: int) -> date:
    text = (raw or "").strip()
    try:
        return datetime.strptime(text, DATE_FORMAT).date()
    except ValueError as exc:
        raise ImportError_(
            f"line {line}: date {raw!r} is not in {DATE_FORMAT} format"
        ) from exc


def normalize_account(raw: str) -> str:
    """Collapse internal whitespace; the export has a trailing space in one name."""
    return " ".join((raw or "").split())


#: casefolded name -> canonical display name. Rebuilt per parse from the file.
CATEGORY_CANONICAL: dict[str, str] = {}


def build_category_canonical(raw_names) -> None:
    """Decide the canonical spelling for each category in the file.

    The export contains case-only duplicates (`ropa` next to `Ropa`). Picking the
    most frequent correctly-capitalised variant keeps the user's own naming rather
    than imposing one, and makes the same typo map onto the same category every run.
    """
    CATEGORY_CANONICAL.clear()
    groups: dict[str, list[str]] = {}
    for raw in raw_names:
        cleaned = " ".join((raw or "").split())
        if cleaned:
            groups.setdefault(cleaned.casefold(), []).append(cleaned)

    for key, variants in groups.items():
        if key in CATEGORY_ALIASES:
            CATEGORY_CANONICAL[key] = CATEGORY_ALIASES[key]
            continue
        # Prefer a variant with letters beyond lowercase, then the most common.
        chosen = max(sorted(variants), key=lambda v: (not v.islower(), variants.count(v)))
        CATEGORY_CANONICAL[key] = chosen


def normalize_category(raw: str) -> str:
    name = " ".join((raw or "").split())
    if not name:
        return UNCATEGORISED
    return CATEGORY_CANONICAL.get(name.casefold(), name)


def infer_account_type(name: str) -> str:
    lowered = name.lower()
    for pattern, account_type in ACCOUNT_TYPE_RULES:
        if re.search(pattern, lowered):
            return account_type
    return Account.Type.OTHER


def make_import_key(
    *,
    ordinal: int,
    account: str,
    currency: str,
    when: date,
    amount: Decimal,
    category: str,
    description: str,
    budget: str,
) -> str:
    """Deterministic identity for a CSV row, so re-importing the same file is a no-op.

    The export has no primary key and the reference column is almost always empty.
    The key is therefore a hash of the row's position plus its content.

    The position matters: the file contains rows that are identical in every field
    and are genuinely separate transactions (four `Runpod` charges of 25.00 on the
    same day, for instance). Hashing content alone would collapse them and silently
    lose money, so the ordinal is part of the identity. Re-importing the *same* file
    still produces the same keys, which is what idempotency requires.
    """
    payload = "|".join(
        [
            str(ordinal),
            account,
            currency,
            when.isoformat(),
            f"{amount:.2f}",
            category,
            description,
            budget,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_csv(path: str | Path, *, strict: bool = True) -> ImportPlan:
    """Read the export into a validated plan. Touches nothing but the file."""
    source = Path(path)
    if not source.is_file():
        raise ImportError_(f"file not found: {source}")

    with source.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        missing = {key: name for key, name in COLUMNS.items() if name not in (reader.fieldnames or [])}
        if missing:
            raise ImportError_(
                f"CSV is missing expected column(s): {', '.join(sorted(missing.values()))}. "
                f"Found: {reader.fieldnames}"
            )
        raw_rows = list(reader)

    # First pass: decide the canonical spelling of every category in the file so
    # that case-only duplicates collapse onto one category.
    build_category_canonical(
        row.get(COLUMNS["category"], "") for row in raw_rows
    )

    plan = ImportPlan()

    for index, row in enumerate(raw_rows, start=2):
        date_raw = (row.get(COLUMNS["date"]) or "").strip()
        amount_raw = (row.get(COLUMNS["amount"]) or "").strip()
        account_raw = normalize_account(row.get(COLUMNS["account"]) or "")
        currency_raw = (row.get(COLUMNS["currency"]) or "").strip()

        def present(*values) -> bool:
            return any((value or "").strip() for value in values)

        # A row with no usable content at all is trailing junk from the export and is
        # always dropped. The real file ends with such a row whose date column holds
        # the text "Toca 1/1/2023" and nothing else.
        if not present(amount_raw, account_raw, currency_raw, date_raw):
            plan.skipped.append((index, "blank row"))
            continue

        # A row that carries some content but no amount and no account holds no
        # transaction, whatever the date column says; that is junk too, not data.
        if not present(amount_raw, account_raw):
            plan.skipped.append((index, "row without an amount or account"))
            continue

        # Anything past this point has content, so a problem is a defect in the file.
        # Missing fields stop the import even in lenient mode: --lenient exists for
        # unparseable values, not for silently dropping money.
        missing = [
            label
            for label, value in (
                ("date", date_raw),
                ("amount", amount_raw),
                ("account", account_raw),
            )
            if not (value or "").strip()
        ]
        if missing:
            raise ImportError_(
                f"line {index}: missing required field(s): {', '.join(missing)}"
            )

        try:
            when = parse_date(date_raw, index)
            amount = parse_amount(amount_raw, index)
        except ImportError_ as exc:
            if strict:
                raise
            plan.skipped.append((index, str(exc)))
            continue

        if amount == 0:
            plan.skipped.append((index, "zero amount"))
            continue
        if not account_raw:
            reason = "missing account name"
            if strict:
                raise ImportError_(f"line {index}: {reason}")
            plan.skipped.append((index, reason))
            continue

        currency_code = CURRENCY_CODES.get(currency_raw.lower())
        if currency_code is None:
            reason = f"unknown currency {currency_raw!r}"
            if strict:
                raise ImportError_(f"line {index}: {reason}")
            plan.skipped.append((index, reason))
            continue

        category = normalize_category(row.get(COLUMNS["category"]) or "")
        description = " ".join((row.get(COLUMNS["description"]) or "").split())
        budget_name = " ".join((row.get(COLUMNS["budget"]) or "").split())
        reference = (row.get(COLUMNS["reference"]) or "").strip()

        if reference:
            # The export flags anomalies in this column; keep the note visible
            # instead of silently dropping it.
            description = f"{description} [{reference}]".strip()

        transaction_type = (
            Transaction.Type.EXPENSE if amount < 0 else Transaction.Type.INCOME
        )
        absolute = abs(amount).quantize(Decimal("0.01"))

        plan.rows.append(
            Row(
                line=index,
                date=when,
                amount=absolute,
                transaction_type=transaction_type,
                category=category,
                account=account_raw,
                currency_code=currency_code,
                budget=budget_name or None,
                description=description,
                reference=reference,
                import_key=make_import_key(
                    ordinal=index,
                    account=account_raw,
                    currency=currency_code,
                    when=when,
                    amount=amount,
                    category=category,
                    description=description,
                    budget=budget_name,
                ),
            )
        )

    if not plan.rows:
        raise ImportError_("no importable rows were found in the file")

    _aggregate(plan)
    return plan


def _aggregate(plan: ImportPlan) -> None:
    """Build the per-account, per-category and per-budget summaries."""
    for row in plan.rows:
        key = (row.account, row.currency_code)
        account = plan.accounts.get(key)
        if account is None:
            account = AccountPlan(
                name=row.account,
                currency_code=row.currency_code,
                account_type=infer_account_type(row.account),
            )
            plan.accounts[key] = account

        account.transaction_count += 1
        account.closing_balance += row.signed_amount
        if row.category == OPENING_CATEGORY:
            account.opening_balance += row.signed_amount
        account.first_date = (
            row.date if account.first_date is None else min(account.first_date, row.date)
        )
        account.last_date = (
            row.date if account.last_date is None else max(account.last_date, row.date)
        )

        plan.categories.add(row.category)
        plan.currencies.add(row.currency_code)
        if row.budget:
            plan.budgets.setdefault(row.budget, []).append(row.date)

    for account in plan.accounts.values():
        account.closing_balance = account.closing_balance.quantize(Decimal("0.01"))
        account.opening_balance = account.opening_balance.quantize(Decimal("0.01"))

    # Flag accounts whose name is ambiguous because it appears in two currencies.
    by_name: dict[str, set[str]] = {}
    for account in plan.accounts.values():
        by_name.setdefault(account.name, set()).add(account.currency_code)
    for name, codes in sorted(by_name.items()):
        if len(codes) > 1:
            plan.warnings.append(
                (
                    0,
                    f"account {name!r} appears in {len(codes)} currencies "
                    f"({', '.join(sorted(codes))}); it will be split one account per currency",
                )
            )


def duplicate_report(plan: ImportPlan) -> list[tuple[tuple, int]]:
    """Rows that are identical in every field except their position in the file.

    Reported for the operator's benefit: they may be genuine repeats (the real
    export has four 25.00 Runpod charges on one day) or a sign of a concatenated
    file. They are imported as separate transactions either way.
    """
    counts: dict[tuple, int] = {}
    for row in plan.rows:
        counts[row.content_signature] = counts.get(row.content_signature, 0) + 1
    return sorted(
        ((signature, count) for signature, count in counts.items() if count > 1),
        key=lambda item: -item[1],
    )


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


@dataclass
class ImportResult:
    accounts_created: list[str] = field(default_factory=list)
    currencies_created: list[str] = field(default_factory=list)
    categories_created: list[str] = field(default_factory=list)
    budgets_created: list[str] = field(default_factory=list)
    transactions_created: int = 0
    transactions_skipped_existing: int = 0
    adjustments: list[tuple[str, Decimal, Decimal]] = field(default_factory=list)
    reconciled: bool = False

    def as_dict(self) -> dict:
        return {
            "accounts_created": self.accounts_created,
            "currencies_created": self.currencies_created,
            "categories_created": self.categories_created,
            "budgets_created": self.budgets_created,
            "transactions_created": self.transactions_created,
            "transactions_skipped_existing": self.transactions_skipped_existing,
            "adjustments": [
                {"account": name, "from": str(before), "to": str(after)}
                for name, before, after in self.adjustments
            ],
            "reconciled": self.reconciled,
        }


def _ensure_currency(code: str) -> tuple[Currency, bool]:
    existing = Currency.objects.filter(code=code).first()
    if existing:
        return existing, False
    name, symbol, rate = CURRENCY_DEFAULTS.get(code, (code, "", Decimal("1")))
    return (
        Currency.objects.create(
            code=code,
            name=name,
            symbol=symbol,
            exchange_rate=rate,
            principal=(code == "USD"),
            is_active=True,
        ),
        True,
    )


def commit_plan(
    plan: ImportPlan,
    *,
    user,
    reconcile: bool = True,
    reset: bool = False,
) -> ImportResult:
    """Write the plan. Everything happens inside one transaction.

    `reconcile` sets each account's final balance to the closing balance the CSV
    implies, recording the difference as an explicit adjustment. `reset` deletes the
    user's existing transactions first, for a clean re-import.
    """
    result = ImportResult()

    with db_transaction.atomic():
        if reset:
            deleted, _ = Transaction.objects.filter(user=user).delete()
            result.transactions_skipped_existing = 0
            _ = deleted  # counts are reported by the caller

        # --- Currencies ----------------------------------------------------
        currencies: dict[str, Currency] = {}
        for code in sorted(plan.currencies):
            currency, created = _ensure_currency(code)
            currencies[code] = currency
            if created:
                result.currencies_created.append(code)

        # --- Accounts ------------------------------------------------------
        accounts: dict[tuple[str, str], Account] = {}
        for key, account_plan in sorted(plan.accounts.items()):
            display_name = account_plan.name
            # Disambiguate only when the same name exists in another currency.
            same_name = [p for k, p in plan.accounts.items() if p.name == account_plan.name]
            if len(same_name) > 1:
                display_name = f"{account_plan.name} ({account_plan.currency_code})"

            account, created = Account.objects.get_or_create(
                user=user,
                name=display_name,
                defaults={
                    "account_type": account_plan.account_type,
                    "currency": currencies[account_plan.currency_code],
                    "balance": Decimal("0.00"),
                    "institution": "",
                    "official_number": "",
                    "is_active": True,
                },
            )
            accounts[key] = account
            if created:
                result.accounts_created.append(display_name)

        # --- Categories ----------------------------------------------------
        categories: dict[str, Category] = {}
        for name in sorted(plan.categories):
            category, created = Category.objects.get_or_create(user=user, name=name)
            categories[name] = category
            if created:
                result.categories_created.append(name)

        # --- Budgets -------------------------------------------------------
        budgets: dict[str, Budget] = {}
        for name, dates in sorted(plan.budgets.items()):
            start, end = min(dates), max(dates)
            currency = currencies.get("USD") or next(iter(currencies.values()))
            # A budget's ceiling is what was actually spent, counting expenses only
            # (the export records no limits of its own).
            spent = sum(
                (
                    row.amount
                    for row in plan.rows
                    if row.budget == name and row.transaction_type == Transaction.Type.EXPENSE
                ),
                Decimal("0.00"),
            )
            budget, created = Budget.objects.get_or_create(
                user=user,
                name=name,
                defaults={
                    "currency": currency,
                    "start_date": start,
                    "end_date": end,
                    # The export has no limits, so the observed spend becomes the
                    # limit: the budget starts fully used instead of inventing an
                    # arbitrary ceiling.
                    "max_amount": spent.quantize(Decimal("0.01")) or Decimal("0.01"),
                    "min_amount": Decimal("0.00"),
                    "is_active": True,
                },
            )
            budgets[name] = budget
            if created:
                result.budgets_created.append(name)

        # --- Transactions --------------------------------------------------
        existing_keys = set(
            Transaction.objects.filter(user=user)
            .exclude(import_key=None)
            .values_list("import_key", flat=True)
        )

        pending: list[Transaction] = []
        for row in plan.rows:
            if row.import_key in existing_keys:
                result.transactions_skipped_existing += 1
                continue
            existing_keys.add(row.import_key)
            account = accounts[(row.account, row.currency_code)]
            pending.append(
                Transaction(
                    user=user,
                    account=account,
                    transaction_type=row.transaction_type,
                    transaction_date=row.date,
                    amount=row.amount,
                    currency=currencies[row.currency_code],
                    description=row.description,
                    category=categories[row.category],
                    budget=budgets.get(row.budget) if row.budget else None,
                    import_key=row.import_key,
                )
            )

        # No explicit batch_size: Django sizes the batch from the backend's variable
        # limit. A hard-coded 500 hits SQLite's MAX_COMPOUND_SELECT of 500 exactly and
        # fails on the second batch with a misleading "unable to open database file".
        Transaction.objects.bulk_create(pending)
        result.transactions_created = len(pending)

        # --- Balances ------------------------------------------------------
        # `bulk_create` deliberately bypasses the service layer (4,441 individual
        # saves would be needlessly slow and the ledger is already consistent), so
        # the cached balance is written here, once per account.
        #
        # With `reconcile` the balance comes from the CSV's closing sum. That is
        # normally identical to the sum of the imported transactions, in which case
        # the account simply moves from its creation default of 0.00 to its real
        # value. When the two differ the gap is reported as an adjustment: it means
        # the export implies capital the ledger cannot account for.
        for key, account_plan in sorted(plan.accounts.items()):
            account = accounts[key]
            derived = _ledger_total(account)
            target = account_plan.closing_balance if reconcile else derived
            if derived != target:
                result.adjustments.append((account.name, derived, target))
            if account.balance != target:
                account.balance = target
                account.save(update_fields=["balance", "last_updated"])
        result.reconciled = reconcile

    return result


def _ledger_total(account: Account) -> Decimal:
    """Balance implied by the account's stored transactions."""
    total = Decimal("0.00")
    for row in (
        Transaction.objects.filter(account=account)
        .values("transaction_type")
        .annotate(total=Sum("amount"))
    ):
        amount = row["total"] or Decimal("0.00")
        if row["transaction_type"] == Transaction.Type.INCOME:
            total += amount
        else:
            total -= amount
    incoming = (
        Transaction.objects.filter(
            destination_account=account,
            transaction_type=Transaction.Type.TRANSFER,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )
    return (total + incoming).quantize(Decimal("0.01"))


def touched_user_check(user) -> None:
    """Refuse to run against a user that already has transactions, unless reset."""
    count = Transaction.objects.filter(user=user).count()
    if count:
        raise ImportError_(
            f"user '{user.username}' already has {count} transaction(s). "
            "Pass --reset to delete them first, or --skip-existing to add only missing rows."
        )


__all__ = [
    "ImportError_",
    "ImportPlan",
    "ImportResult",
    "Row",
    "commit_plan",
    "duplicate_report",
    "parse_csv",
    "touched_user_check",
]
