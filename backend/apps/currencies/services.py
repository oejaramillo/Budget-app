"""Exchange-rate acquisition.

The only external dependency is the provider HTTP API. All parsing happens here
so views and management commands stay thin, and every rate is coerced to
`Decimal` before it reaches the database.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Currency, ExchangeRateHistory, ExchangeRateSnapshot

logger = logging.getLogger(__name__)


class ExchangeRateError(RuntimeError):
    """Raised when rates cannot be fetched or parsed."""


@dataclass
class RefreshResult:
    updated: list[str] = field(default_factory=list)
    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    source: str = ""
    succeeded: bool = True
    message: str = ""

    @property
    def updated_count(self) -> int:
        return len(self.updated)

    @property
    def created_count(self) -> int:
        return len(self.created)


def fetch_rates(base_code: str | None = None) -> tuple[str, dict[str, Decimal]]:
    """Return `(base_code, {code: rate})` from the configured provider."""
    api_key = settings.EXCHANGE_API_KEY
    if not api_key:
        raise ExchangeRateError(
            "EXCHANGE_API_KEY is not configured; cannot refresh rates."
        )

    base = (base_code or settings.BASE_CURRENCY_CODE).upper()
    url = f"{settings.EXCHANGE_API_BASE_URL}/{api_key}/latest/{base}"

    try:
        response = requests.get(url, timeout=settings.EXCHANGE_API_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise ExchangeRateError(f"Could not reach the exchange-rate provider: {exc}") from exc

    if response.status_code != 200:
        raise ExchangeRateError(
            f"Provider returned HTTP {response.status_code}: {response.text[:200]}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise ExchangeRateError("Provider returned a non-JSON response.") from exc

    if payload.get("result") == "error":
        raise ExchangeRateError(payload.get("error-type", "unknown provider error"))

    raw_rates = payload.get("conversion_rates") or {}
    if not raw_rates:
        raise ExchangeRateError("Provider response contained no conversion rates.")

    rates: dict[str, Decimal] = {}
    for code, value in raw_rates.items():
        try:
            rate = Decimal(str(value))
        except (InvalidOperation, TypeError):
            logger.warning("Skipping unparseable rate for %s: %r", code, value)
            continue
        if rate <= 0:
            logger.warning("Skipping non-positive rate for %s: %r", code, rate)
            continue
        rates[str(code).upper()] = rate

    return base, rates


@transaction.atomic
def refresh_rates(
    *, base_code: str | None = None, create_missing: bool = True
) -> RefreshResult:
    """Fetch rates and persist them, recording an audit snapshot."""
    base, rates = fetch_rates(base_code)
    base_currency = Currency.objects.filter(code=base).first()
    if base_currency and base_currency.exchange_rate != Decimal("1"):
        # The base currency is the denominator of every stored rate.
        base_currency.exchange_rate = Decimal("1")
        base_currency.principal = True
        base_currency.save(update_fields=["exchange_rate", "principal", "rate_updated_at"])

    result = RefreshResult(source=f"{settings.EXCHANGE_API_BASE_URL} ({base})")

    existing = {c.code: c for c in Currency.objects.all()}
    history: list[ExchangeRateHistory] = []

    for code, rate in sorted(rates.items()):
        currency = existing.get(code)
        if currency is None:
            if not create_missing:
                result.skipped.append(code)
                continue
            currency = Currency.objects.create(
                code=code,
                name=code,
                exchange_rate=rate,
                principal=(code == base),
                is_active=True,
            )
            existing[code] = currency
            result.created.append(code)
        else:
            currency.exchange_rate = rate
            currency.principal = code == base or currency.principal
            currency.rate_updated_at = timezone.now()
            currency.save(
                update_fields=["exchange_rate", "principal", "rate_updated_at"]
            )
            result.updated.append(code)

        history.append(ExchangeRateHistory(currency=currency, rate=rate))

    snapshot = ExchangeRateSnapshot.objects.create(
        source=result.source,
        base_code=base,
        updated_count=result.updated_count,
        created_count=result.created_count,
        succeeded=True,
    )
    ExchangeRateHistory.objects.bulk_create(history, ignore_conflicts=True)

    result.message = (
        f"{result.updated_count} rate(s) updated, {result.created_count} currency(ies) created."
    )
    logger.info("Exchange rates refreshed: %s", result.message)
    return result


def record_failure(source: str, base_code: str, message: str) -> None:
    """Persist a failed refresh so the failure is visible in the admin."""
    ExchangeRateSnapshot.objects.create(
        source=source,
        base_code=base_code,
        succeeded=False,
        message=message[:2000],
    )
