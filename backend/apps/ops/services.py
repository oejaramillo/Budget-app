"""Maintenance operations exposed to the superuser console.

Design rules, in order of importance:

1. **An allowlist, never a shell.** Operations are Python callables registered with
   an explicit, typed argument spec. Nothing here builds a command string, so no
   operator input ever reaches a shell.
2. **Every run is recorded.** `execute_operation` writes an `OperationRun` row
   before the callable starts and updates it afterwards, so a crash still leaves
   evidence.
3. **Safety is declared, not implied.** Each operation carries a `Safety` level and
   the registry refuses to run levels the operator has not enabled in
   `OpsSettings`.
4. **Read-only work is honest.** Checks and statistics return data; they never
   "fix" anything silently.
"""

from __future__ import annotations

import logging
import time
import traceback
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Iterable

from django.apps import apps as django_apps
from django.conf import settings
from django.db import connection
from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from .models import OperationRun, OpsSettings

logger = logging.getLogger(__name__)


class Safety(str, Enum):
    """How dangerous an operation is."""

    #: Reads only; safe to offer anywhere.
    READ = "read"
    #: Writes to application data but is reversible/idempotent.
    MUTATE = "mutate"
    #: Can break the running service (schema changes, mass deletion).
    DESTRUCTIVE = "destructive"


class OperationError(RuntimeError):
    """Raised when an operation cannot run or reports a failure."""


@dataclass(frozen=True)
class FieldSpec:
    """One input rendered as a form control in the console."""

    name: str
    label: str
    type: str = "string"  # string | integer | boolean | select
    required: bool = False
    default: Any = None
    help_text: str = ""
    choices: tuple[tuple[str, str], ...] = ()
    #: Value that makes the operation behave differently enough to deserve a warning.
    caution: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "type": self.type,
            "required": self.required,
            "default": self.default,
            "help_text": self.help_text,
            "choices": [{"value": value, "label": label} for value, label in self.choices],
            "caution": self.caution,
        }


@dataclass(frozen=True)
class OperationSpec:
    """A maintenance operation the console may run."""

    key: str
    label: str
    description: str
    safety: Safety
    handler: Callable[..., dict]
    fields: tuple[FieldSpec, ...] = ()
    group: str = "General"

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "description": self.description,
            "safety": self.safety.value,
            "group": self.group,
            "fields": [f.to_dict() for f in self.fields],
        }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, OperationSpec] = {}


def register(spec: OperationSpec) -> OperationSpec:
    if spec.key in _REGISTRY:  # pragma: no cover - programming error
        raise RuntimeError(f"Duplicate operation key: {spec.key}")
    _REGISTRY[spec.key] = spec
    return spec


def all_operations() -> list[OperationSpec]:
    return sorted(_REGISTRY.values(), key=lambda spec: (spec.group, spec.label))


def get_operation(key: str) -> OperationSpec | None:
    return _REGISTRY.get(key)


# ---------------------------------------------------------------------------
# Argument coercion
# ---------------------------------------------------------------------------

_TRUE = {"1", "true", "yes", "on", "y", "t"}


def _coerce(spec: FieldSpec, raw: Any) -> Any:
    """Turn a JSON/form value into the type the handler expects."""
    if raw is None or raw == "":
        if spec.required and spec.default is None:
            raise OperationError(f"'{spec.label}' is required.")
        return spec.default

    if spec.type == "boolean":
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().lower() in _TRUE

    if spec.type == "integer":
        try:
            return int(raw)
        except (TypeError, ValueError) as exc:
            raise OperationError(f"'{spec.label}' must be a whole number.") from exc

    if spec.type == "select":
        allowed = {value for value, _ in spec.choices}
        value = str(raw)
        if allowed and value not in allowed:
            raise OperationError(
                f"'{spec.label}' must be one of: {', '.join(sorted(allowed))}."
            )
        return value

    return str(raw).strip()


def clean_arguments(spec: OperationSpec, raw: dict | None) -> dict:
    """Validate and normalise an incoming argument dict against the spec."""
    raw = raw or {}
    if not isinstance(raw, dict):
        raise OperationError("Arguments must be a JSON object.")

    known = {f.name for f in spec.fields}
    unknown = set(raw) - known
    if unknown:
        raise OperationError(f"Unknown argument(s): {', '.join(sorted(unknown))}.")

    return {f.name: _coerce(f, raw.get(f.name)) for f in spec.fields}


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def is_allowed(spec: OperationSpec, ops_settings: OpsSettings) -> tuple[bool, str]:
    """Whether the declared safety level is currently permitted."""
    if spec.safety is Safety.DESTRUCTIVE and not ops_settings.allow_destructive_operations:
        return False, (
            "Destructive operations are disabled. Enable them in Operations settings, "
            "or run the command from the server CLI."
        )
    if spec.safety is Safety.MUTATE and not ops_settings.allow_mutating_operations:
        return False, "Mutating operations are disabled in Operations settings."
    return True, ""


def execute_operation(
    spec: OperationSpec,
    arguments: dict,
    *,
    user=None,
    enforce_policy: bool = True,
) -> OperationRun:
    """Run `spec`, recording the attempt and outcome.

    The callable runs synchronously: every operation here is expected to finish in
    single-digit seconds. If one ever needs to be long-running it should record
    intent and hand off to a worker rather than block the request.
    """
    ops_settings = OpsSettings.load()
    if enforce_policy:
        allowed, reason = is_allowed(spec, ops_settings)
        if not allowed:
            raise OperationError(reason)

    run = OperationRun.objects.create(
        operation=spec.key,
        arguments=arguments,
        status=OperationRun.Status.RUNNING,
        triggered_by=user if getattr(user, "is_authenticated", False) else None,
    )

    started = time.monotonic()
    try:
        result = spec.handler(**arguments) or {}
    except Exception as exc:  # noqa: BLE001 - the audit trail must capture anything
        run.status = OperationRun.Status.FAILED
        run.error = f"{exc.__class__.__name__}: {exc}"
        run.output = traceback.format_exc(limit=8)
        run.duration_ms = int((time.monotonic() - started) * 1000)
        run.finished_at = timezone.now()
        run.save()
        logger.exception("Operation %s failed", spec.key)
        raise
    else:
        status = result.pop("_status", OperationRun.Status.SUCCESS)
        run.status = status
        run.result = _json_safe(result)
        run.output = str(result.get("message", ""))
        if status == OperationRun.Status.SKIPPED and not run.output:
            run.output = "Nothing to do."
        run.duration_ms = int((time.monotonic() - started) * 1000)
        run.finished_at = timezone.now()
        run.save()
        logger.info("Operation %s finished as %s", spec.key, status)
        return run


def _json_safe(value: Any) -> Any:
    """Make a handler result JSON-serialisable (Decimal and dates appear often)."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


# ---------------------------------------------------------------------------
# Operation: system statistics
# ---------------------------------------------------------------------------


def collect_system_stats() -> dict:
    """Counts across the whole service plus the rate-refresh audit trail.

    Superuser-only: these numbers span every tenant, unlike the per-user report
    endpoints.
    """
    from apps.accounts.models import Account
    from apps.budgets.models import Budget
    from apps.currencies.models import Currency, ExchangeRateSnapshot
    from apps.investments.models import Holding, Valuation
    from apps.transactions.models import Category, Transaction

    from django.contrib.auth.models import User

    totals = {
        "users": User.objects.count(),
        "active_users": User.objects.filter(is_active=True).count(),
        "staff_users": User.objects.filter(is_staff=True).count(),
        "superusers": User.objects.filter(is_superuser=True).count(),
        "accounts": Account.objects.count(),
        "transactions": Transaction.objects.count(),
        "categories": Category.objects.count(),
        "budgets": Budget.objects.count(),
        "currencies": Currency.objects.count(),
        "active_currencies": Currency.objects.filter(is_active=True).count(),
        "holdings": Holding.objects.count(),
        "valuations": Valuation.objects.count(),
    }

    transactions_by_type = {
        row["transaction_type"]: row["count"]
        for row in Transaction.objects.values("transaction_type").annotate(count=Count("id"))
    }

    # Per-tenant footprint, so a runaway account is visible at a glance.
    busiest_users = list(
        User.objects.annotate(
            account_count=Count("accounts", distinct=True),
            transaction_count=Count("transactions", distinct=True),
        )
        .filter(Q(account_count__gt=0) | Q(transaction_count__gt=0))
        .order_by("-transaction_count")
        .values("id", "username", "account_count", "transaction_count")[:10]
    )

    newest_transaction = Transaction.objects.order_by("-transaction_date").first()
    last_snapshot = ExchangeRateSnapshot.objects.order_by("-fetched_at").first()
    failed_snapshots = ExchangeRateSnapshot.objects.filter(succeeded=False).count()

    return _json_safe({
        "totals": totals,
        "transactions_by_type": transactions_by_type,
        "busiest_users": busiest_users,
        "database": _database_info(),
        "rates": {
            "last_refresh_at": last_snapshot.fetched_at if last_snapshot else None,
            "last_refresh_succeeded": last_snapshot.succeeded if last_snapshot else None,
            "failed_refreshes": failed_snapshots,
            "stale_currencies": rate_freshness()["stale_count"],
        },
        "latest_transaction_date": newest_transaction.transaction_date
        if newest_transaction
        else None,
        "generated_at": timezone.now(),
        "message": "Statistics collected.",
    })


def _database_info() -> dict:
    """Vendor, version and on-disk size where the backend can report it."""
    # Django's SQLite backend stores NAME as a Path, which is not JSON
    # serialisable; the console only ever displays it, so stringify up front.
    raw_name = connection.settings_dict.get("NAME")
    info: dict[str, Any] = {
        "vendor": connection.vendor,
        "name": str(raw_name) if raw_name is not None else None,
        "size_pretty": None,
        "size_bytes": None,
    }
    try:
        with connection.cursor() as cursor:
            if connection.vendor == "postgresql":
                cursor.execute("SELECT version()")
                info["version"] = cursor.fetchone()[0].split(",")[0]
                cursor.execute("SELECT pg_database_size(current_database())")
                size = cursor.fetchone()[0]
                info["size_bytes"] = size
                info["size_pretty"] = _human_bytes(size)
            elif connection.vendor == "sqlite":
                cursor.execute("SELECT sqlite_version()")
                info["version"] = f"SQLite {cursor.fetchone()[0]}"
                cursor.execute(
                    "SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()"
                )
                size = cursor.fetchone()[0] or 0
                info["size_bytes"] = size
                info["size_pretty"] = _human_bytes(size)
            else:  # pragma: no cover - other vendors are not targeted
                cursor.execute("SELECT 1")
    except Exception as exc:  # pragma: no cover - depends on the driver
        info["error"] = str(exc)
    return info


def _human_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} TB"  # pragma: no cover - unreachable


def rate_freshness(max_age_hours: int = 48) -> dict:
    """How old the currency rates are, and which are older than `max_age_hours`."""
    from apps.currencies.models import Currency

    threshold = timezone.now() - timezone.timedelta(hours=max_age_hours)
    stale = list(
        Currency.objects.filter(is_active=True)
        .filter(Q(rate_updated_at__lt=threshold) | Q(rate_updated_at__isnull=True))
        .order_by("code")
        .values_list("code", flat=True)
    )
    newest = (
        Currency.objects.exclude(rate_updated_at=None)
        .order_by("-rate_updated_at")
        .values_list("rate_updated_at", flat=True)
        .first()
    )
    return _json_safe(
        {
            "max_age_hours": max_age_hours,
            "last_refresh_at": newest,
            "age_hours": (
                round((timezone.now() - newest).total_seconds() / 3600, 2) if newest else None
            ),
            "is_stale": newest is None or newest < threshold,
            "stale_count": len(stale),
            "stale_codes": stale[:50],
        }
    )


# ---------------------------------------------------------------------------
# Operation: data integrity check
# ---------------------------------------------------------------------------

#: Balance comparisons round to cents; anything smaller is noise, not corruption.
_CENT = Decimal("0.01")


def check_data_integrity() -> dict:
    """Look for conditions that mean stored data disagrees with the rules.

    Read-only by design: this reports, it never repairs. A human decides whether a
    finding is a bug or a legitimate edge case.
    """
    findings: list[dict] = []

    def add(severity: str, code: str, summary: str, items: Iterable) -> None:
        items = list(items)
        if items:
            findings.append(
                {
                    "severity": severity,
                    "code": code,
                    "summary": summary,
                    "count": len(items),
                    "samples": items[:20],
                }
            )

    findings.extend(_check_currency_rules())
    findings.extend(_check_account_balances())
    findings.extend(_check_transaction_rules())
    findings.extend(_check_tenant_links())

    errors = sum(f["count"] for f in findings if f["severity"] == "error")
    warnings = sum(f["count"] for f in findings if f["severity"] == "warning")
    return _json_safe({
        "findings": findings,
        "error_count": errors,
        "warning_count": warnings,
        "checked_at": timezone.now(),
        "message": (
            "No issues found."
            if not findings
            else f"{errors} error(s) and {warnings} warning(s) across {len(findings)} check(s)."
        ),
    })


def _check_currency_rules() -> list[dict]:
    from apps.currencies.models import Currency

    findings: list[dict] = []

    principal_count = Currency.objects.filter(principal=True).count()
    if principal_count == 0:
        findings.append(
            {
                "severity": "error",
                "code": "no_principal_currency",
                "summary": (
                    "No principal reporting currency is set. Reports cannot be converted "
                    "into a single currency."
                ),
                "count": 1,
                "samples": [],
            }
        )
    elif principal_count > 1:  # pragma: no cover - blocked by a DB constraint
        findings.append(
            {
                "severity": "error",
                "code": "multiple_principal_currencies",
                "summary": "More than one principal currency exists.",
                "count": principal_count,
                "samples": list(
                    Currency.objects.filter(principal=True).values_list("code", flat=True)
                ),
            }
        )

    findings.extend(
        _as_finding(
            "error",
            "inactive_principal_currency",
            "The principal currency is marked inactive.",
            Currency.objects.filter(principal=True, is_active=False).values_list(
                "code", flat=True
            ),
        )
    )
    findings.extend(
        _as_finding(
            "error",
            "non_positive_exchange_rate",
            "Currencies with a non-positive rate would corrupt every conversion.",
            Currency.objects.filter(exchange_rate__lte=0).values_list("code", flat=True),
        )
    )
    findings.extend(
        _as_finding(
            "warning",
            "base_currency_rate_not_one",
            f"The base currency ({settings.BASE_CURRENCY_CODE}) should have a rate of exactly 1.",
            Currency.objects.filter(code=settings.BASE_CURRENCY_CODE)
            .exclude(exchange_rate=1)
            .values_list("code", flat=True),
        )
    )
    findings.extend(
        _as_finding(
            "warning",
            "rates_never_refreshed",
            "Active currencies whose rate has never been refreshed.",
            Currency.objects.filter(is_active=True, rate_updated_at__isnull=True).values_list(
                "code", flat=True
            ),
        )
    )
    findings.extend(
        _as_finding(
            "info",
            "unused_currencies",
            "Active currencies that no account, transaction or holding uses.",
            Currency.objects.filter(is_active=True)
            .annotate(
                usage=Count("accounts", distinct=True)
                + Count("transactions", distinct=True)
                + Count("holdings", distinct=True)
            )
            .filter(usage=0)
            .values_list("code", flat=True),
        )
    )
    return findings


def _check_account_balances() -> list[dict]:
    """Compare the cached `Account.balance` with the ledger.

    The ledger is authoritative: `balance` is a cache updated on every transaction
    write, so a mismatch means a write path bypassed the service layer (a manual
    edit in the shell or the Django admin, typically).
    """
    from apps.accounts.models import Account
    from apps.transactions.models import Transaction

    mismatches = []
    for account in Account.objects.select_related("user").iterator():
        expected = Decimal("0.00")
        for row in (
            Transaction.objects.filter(account=account)
            .values("transaction_type")
            .annotate(total=Sum("amount"))
        ):
            amount = row["total"] or Decimal("0.00")
            if row["transaction_type"] == Transaction.Type.INCOME:
                expected += amount
            else:
                expected -= amount
        # Incoming transfers land on `destination_account`.
        incoming = (
            Transaction.objects.filter(
                destination_account=account, transaction_type=Transaction.Type.TRANSFER
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )
        expected += incoming
        delta = (account.balance - expected).quantize(_CENT)
        if abs(delta) >= _CENT:
            mismatches.append(
                {
                    "account_id": account.pk,
                    "username": account.user.username,
                    "name": account.name,
                    "recorded": str(account.balance),
                    "from_transactions": str(expected.quantize(_CENT)),
                    "difference": str(delta),
                }
            )

    return _as_finding(
        "error",
        "account_balance_mismatch",
        (
            "Accounts whose cached balance differs from the sum of their transactions. "
            "Fix with the account's adjust-balance endpoint, or by re-saving the "
            "transactions through the API."
        ),
        mismatches,
    )


def _check_transaction_rules() -> list[dict]:
    from apps.transactions.models import Transaction

    findings: list[dict] = []

    findings.extend(
        _as_finding(
            "error",
            "non_positive_amount",
            "Transactions with a zero or negative amount violate the ledger rules.",
            Transaction.objects.filter(amount__lte=0).values_list("id", flat=True),
        )
    )
    findings.extend(
        _as_finding(
            "error",
            "transfer_without_destination",
            "Transfers missing a destination account (only possible if a constraint was bypassed).",
            Transaction.objects.filter(
                transaction_type=Transaction.Type.TRANSFER, destination_account__isnull=True
            ).values_list("id", flat=True),
        )
    )
    findings.extend(
        _as_finding(
            "error",
            "transfer_same_account",
            "Transfers whose source and destination are the same account.",
            Transaction.objects.filter(destination_account=F("account")).values_list(
                "id", flat=True
            ),
        )
    )
    findings.extend(
        _as_finding(
            "warning",
            "foreign_currency_without_rate",
            (
                "Transactions whose currency differs from their account's without an "
                "explicit exchange rate; their reporting value is ambiguous."
            ),
            Transaction.objects.exclude(currency=F("account__currency"))
            .filter(exchange_rate__isnull=True)
            .values_list("id", flat=True),
        )
    )
    findings.extend(
        _as_finding(
            "warning",
            "transaction_account_currency_mismatch",
            "Transactions whose account belongs to a different user.",
            Transaction.objects.exclude(account__user=F("user")).values_list("id", flat=True),
        )
    )
    return findings


def _check_tenant_links() -> list[dict]:
    """Cross-tenant references that should be impossible."""
    from apps.investments.models import Holding
    from apps.transactions.models import Category, Transaction

    findings: list[dict] = []

    findings.extend(
        _as_finding(
            "warning",
            "category_budget_owner_mismatch",
            "Categories attached to another user's budget.",
            Category.objects.filter(budget__isnull=False)
            .exclude(budget__user=F("user"))
            .values_list("id", flat=True),
        )
    )
    findings.extend(
        _as_finding(
            "warning",
            "transaction_budget_owner_mismatch",
            "Transactions linked to another user's budget.",
            Transaction.objects.filter(budget__isnull=False)
            .exclude(budget__user=F("user"))
            .values_list("id", flat=True),
        )
    )
    findings.extend(
        _as_finding(
            "warning",
            "holding_account_owner_mismatch",
            "Holdings pointing at another user's account.",
            Holding.objects.filter(account__isnull=False)
            .exclude(account__user=F("user"))
            .values_list("id", flat=True),
        )
    )
    return findings


def _as_finding(severity: str, code: str, summary: str, items) -> list[dict]:
    items = list(items)
    if not items:
        return []
    return [
        {
            "severity": severity,
            "code": code,
            "summary": summary,
            "count": len(items),
            "samples": items[:20],
        }
    ]


# ---------------------------------------------------------------------------
# Operation: refresh rates (wraps the existing management command)
# ---------------------------------------------------------------------------


def run_refresh_currencies(base: str | None = None, force: bool = False, create_missing: bool = True) -> dict:
    """Refresh rates by calling the same code path as `manage.py refresh_currencies`.

    Deliberately not `call_command`: importing the service keeps one implementation
    and avoids stdout capture games.
    """
    from apps.currencies.services import ExchangeRateError, record_failure, refresh_rates

    base_code = (base or settings.BASE_CURRENCY_CODE).upper()

    if not force:
        freshness = rate_freshness(max_age_hours=6)
        if freshness["last_refresh_at"] and not freshness["is_stale"]:
            return {
                "_status": OperationRun.Status.SKIPPED,
                "message": (
                    f"Rates were refreshed {freshness['age_hours']}h ago. "
                    "Use 'force' to refresh anyway."
                ),
                "freshness": freshness,
            }

    try:
        result = refresh_rates(base_code=base_code, create_missing=create_missing)
    except ExchangeRateError as exc:
        record_failure("exchangerate-api", base_code, str(exc))
        raise OperationError(str(exc)) from exc

    return {
        "message": result.message,
        "base": base_code,
        "updated": result.updated,
        "created": result.created,
        "skipped": result.skipped,
        "freshness": rate_freshness(max_age_hours=6),
    }


# ---------------------------------------------------------------------------
# Operation: run migrations (opt-in)
# ---------------------------------------------------------------------------


def run_migrations() -> dict:
    """Apply pending migrations.

    Disabled by default (`OpsSettings.allow_destructive_operations`). Schema changes
    from a web request are a bad habit: a failure mid-migration can leave the
    service unable to boot, and the CLI is always available.
    """
    from django.core.management import call_command
    from io import StringIO

    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    pending = executor.migration_plan(executor.loader.graph.leaf_nodes())
    if not pending:
        return {"message": "No pending migrations.", "applied": []}

    buffer = StringIO()
    call_command("migrate", "--noinput", stdout=buffer, stderr=buffer)
    applied = [f"{migration.app_label}.{migration.name}" for migration, _ in pending]
    return {
        "message": f"Applied {len(applied)} migration(s).",
        "applied": applied,
        "output": buffer.getvalue(),
    }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

register(
    OperationSpec(
        key="refresh_currencies",
        label="Refresh currency rates",
        description=(
            "Fetch current exchange rates from the configured provider and update the "
            "currency catalogue. Runs the same code as `manage.py refresh_currencies`."
        ),
        safety=Safety.MUTATE,
        group="Currencies",
        handler=run_refresh_currencies,
        fields=(
            FieldSpec(
                name="base",
                label="Base currency",
                type="string",
                default=None,
                help_text=f"ISO code to quote rates against. Defaults to {settings.BASE_CURRENCY_CODE}.",
            ),
            FieldSpec(
                name="force",
                label="Force refresh",
                type="boolean",
                default=False,
                help_text="Refresh even when rates are less than 6 hours old.",
            ),
            FieldSpec(
                name="create_missing",
                label="Create missing currencies",
                type="boolean",
                default=True,
                help_text="Insert currencies returned by the provider that are not stored yet.",
            ),
        ),
    )
)

register(
    OperationSpec(
        key="integrity_check",
        label="Data integrity check",
        description=(
            "Read-only sweep for conditions that indicate stored data disagrees with "
            "the application rules: balance drift, broken tenant links, invalid rates "
            "and transactions that bypassed the service layer."
        ),
        safety=Safety.READ,
        group="Checks",
        handler=check_data_integrity,
    )
)

register(
    OperationSpec(
        key="system_stats",
        label="System statistics",
        description=(
            "Counts for users, accounts, transactions, budgets, holdings and "
            "currencies, plus database size and rate freshness."
        ),
        safety=Safety.READ,
        group="Checks",
        handler=collect_system_stats,
    )
)

register(
    OperationSpec(
        key="run_migrations",
        label="Apply pending migrations",
        description=(
            "Apply outstanding database migrations. Disabled by default: prefer "
            "`manage.py migrate` from the CLI, where a failure is visible and "
            "recoverable."
        ),
        safety=Safety.DESTRUCTIVE,
        group="Danger zone",
        handler=run_migrations,
    )
)


def registry_payload() -> list[dict]:
    """The registry as the console consumes it, annotated with current policy."""
    ops_settings = OpsSettings.load()
    payload = []
    for spec in all_operations():
        allowed, reason = is_allowed(spec, ops_settings)
        item = spec.to_dict()
        item["allowed"] = allowed
        item["blocked_reason"] = reason
        payload.append(item)
    return payload


def app_inventory() -> list[dict]:
    """Local apps with their model names, for the system overview card."""
    inventory = []
    for config in django_apps.get_app_configs():
        if not config.name.startswith("apps."):
            continue
        inventory.append(
            {
                "label": config.verbose_name,
                "name": config.name,
                "models": sorted(
                    model.__name__ for model in config.get_models()
                ),
            }
        )
    return sorted(inventory, key=lambda item: item["name"])
