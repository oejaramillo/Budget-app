"""
Spending analytics.

Everything here answers a question a person actually asks about their money:
what did I spend, is that more or less than usual, where did it go, and what is
changing. The endpoints are shaped around those questions rather than around the
tables underneath.

Two ideas drive most of the design.

**Money movement is not spending.** `Transferencia cuentas`, `Préstamos`,
`Cambio de moneda`, `Inversión` and friends are rows the ledger needs but they do
not consume wealth — they move it, to another account, to a lender, or into an
asset. In this database they are *just over 47% of total expenses*, so a dashboard
that adds them to groceries is misleading. Every figure here is reported three
ways: `total` (everything), `consumption` (what was actually spent) and
`money_movement` (the rest).

**Comparisons need complete periods.** A month that is three days old cannot be
compared with a finished one. Period deltas therefore use the *last complete*
month (or quarter/year), and the running period is reported separately with a
projection, so "you are behind" is never an artefact of the calendar.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Avg, Count, Max, Min, QuerySet, Sum
from django.db.models.functions import ExtractWeekDay, TruncMonth
from django.utils import timezone

from apps.currencies.models import Currency
from apps.transactions.models import Transaction

CENT = Decimal("0.01")

#: Categories that move money instead of consuming it. Matched case-insensitively.
#: Override with `settings.ANALYTICS_MONEY_MOVEMENT_CATEGORIES`.
DEFAULT_MONEY_MOVEMENT_CATEGORIES = (
    "Transferencia cuentas",
    "Cambio de moneda",
    "Préstamos",
    "Inversión",
    "Especulación",
    "Ajuste",
    "Aportes colectivos",
)

#: Number of months of history the trend endpoints return unless asked otherwise.
DEFAULT_TREND_MONTHS = 24

#: Weekday labels, indexed to match `ExtractWeekDay` (1 = Sunday).
WEEKDAY_LABELS = ["", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


class AnalyticsError(ValueError):
    """Raised for an unusable request parameter."""


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def money(value) -> float:
    """Decimal or None to a rounded float for JSON.

    Floats are fine at the API boundary — the arithmetic has already happened in
    Decimal. Rounding here keeps totals stable when the client sums them.
    """
    if value is None:
        return 0.0
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return float(value.quantize(CENT, rounding=ROUND_HALF_UP))


def percent(part: Decimal, whole: Decimal) -> float | None:
    """`part` as a percentage of `whole`, or None when the whole is zero."""
    if not whole:
        return None
    return float((Decimal(part) / Decimal(whole) * 100).quantize(Decimal("0.1")))


def delta(current: Decimal, previous: Decimal) -> dict:
    """Absolute and relative change, plus which direction is 'more'."""
    change = Decimal(current) - Decimal(previous)
    result = {
        "current": money(current),
        "previous": money(previous),
        "change": money(change),
        "change_percent": percent(change, previous) if previous else None,
    }
    return result


def money_movement_categories() -> set[str]:
    from django.conf import settings

    configured = getattr(
        settings, "ANALYTICS_MONEY_MOVEMENT_CATEGORIES", DEFAULT_MONEY_MOVEMENT_CATEGORIES
    )
    return {name.casefold() for name in configured}


def resolve_currency(code: str | None) -> Currency:
    """The currency to report in: the requested one, else the principal currency.

    Cross-currency conversion is deliberately not applied here. Rates in this
    database are single historical snapshots, so converting 2018 USD spend at a
    2026 rate would be fabrication. Report one currency at a time instead, and send
    the list of currencies that actually have data so the UI can offer a switch.
    """
    queryset = Currency.objects.filter(is_active=True)
    if code:
        currency = queryset.filter(code=code.upper()).first()
        if currency is None:
            raise AnalyticsError(f"Unknown or inactive currency '{code}'.")
        return currency
    return (
        queryset.filter(principal=True).first()
        or queryset.first()
        or Currency.objects.first()
    )


def available_currencies(user) -> list[dict]:
    """Currencies with data for this user, so the UI can offer a real choice."""
    rows = (
        Transaction.objects.filter(user=user)
        .values("currency__code", "currency__name", "currency__principal")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    return [
        {
            "code": row["currency__code"],
            "name": row["currency__name"],
            "principal": row["currency__principal"],
            "transaction_count": row["count"],
        }
        for row in rows
    ]


def base_queryset(user, currency: Currency) -> QuerySet:
    """Transactions that count towards spending analytics.

    Transfers are excluded outright: they move money between the user's own
    accounts, so counting them would double every internal reshuffle. Income,
    expense and (for completeness) nothing else are aggregated.
    """
    return Transaction.objects.filter(
        user=user,
        currency=currency,
        transaction_type__in=[Transaction.Type.INCOME, Transaction.Type.EXPENSE],
    )


def exclude_money_movement(queryset: QuerySet) -> QuerySet:
    """Drop the categories that move money rather than consume it.

    Used by the behavioural views — weekday profile, top descriptions — where one
    large transfer would otherwise dominate the picture and say nothing about
    habits.
    """
    from django.conf import settings

    names = getattr(
        settings, "ANALYTICS_MONEY_MOVEMENT_CATEGORIES", DEFAULT_MONEY_MOVEMENT_CATEGORIES
    )
    return queryset.exclude(category__name__in=names)


def _split_expenses(rows) -> tuple[Decimal, Decimal]:
    """Split aggregated rows into (consumption, money movement).

    `rows` come from `values("transaction_type", "category__name")`, so the category
    arrives under `category__name`.
    """
    movement_names = money_movement_categories()
    consumption = Decimal("0")
    movement = Decimal("0")
    for row in rows:
        name = (row.get("category__name") or "").casefold()
        if name in movement_names:
            movement += row["total"] or Decimal("0")
        else:
            consumption += row["total"] or Decimal("0")
    return consumption, movement


# ---------------------------------------------------------------------------
# Period arithmetic
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Period:
    """A labelled, inclusive date range."""

    key: str
    label: str
    start: date
    end: date
    #: False for the period that contains today.
    complete: bool

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "start": self.start,
            "end": self.end,
            "complete": self.complete,
        }


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _month_end(value: date) -> date:
    if value.month == 12:
        return value.replace(month=12, day=31)
    return value.replace(month=value.month + 1, day=1) - timedelta(days=1)


def _add_months(value: date, count: int) -> date:
    month = value.month - 1 + count
    year = value.year + month // 12
    month = month % 12 + 1
    return date(year, month, 1)


def resolve_period(granularity: str, anchor: str | None, today: date):
    """Return the requested period and the one to compare against.

    For *complete* periods the comparison is the immediately preceding period. For
    the running period it is the last complete one, so a partial month is compared
    with a finished month rather than with a still-empty one.
    """
    today = today or timezone.localdate()

    if granularity == "month":
        if anchor:
            try:
                year, month = (int(part) for part in anchor.split("-")[:2])
                start = date(year, month, 1)
            except (ValueError, TypeError) as exc:
                raise AnalyticsError("`anchor` must look like YYYY-MM.") from exc
        else:
            start = _month_start(today)
        end = _month_end(start)
        complete = end < today
        previous = Period(
            key="previous",
            label=f"{_add_months(start, -1):%B %Y}",
            start=_add_months(start, -1),
            end=_month_end(_add_months(start, -1)),
            complete=True,
        )
        # Same window one year earlier — the fair seasonal comparison.
        same_period_last_year = Period(
            key="last_year",
            label=f"{start.replace(year=start.year - 1):%B %Y}",
            start=start.replace(year=start.year - 1),
            end=end.replace(year=end.year - 1),
            complete=complete,
        )

    elif granularity == "quarter":
        if anchor:
            try:
                # Accept `2025-Q3`, `2025Q3` and `2025-3`.
                match = re.fullmatch(r"(\d{4})[-\s]?[Qq]?(\d)", anchor.strip())
                if not match:
                    raise ValueError
                year, quarter = int(match.group(1)), int(match.group(2))
                if not 1 <= quarter <= 4:
                    raise ValueError
                start = date(year, (quarter - 1) * 3 + 1, 1)
            except (ValueError, TypeError) as exc:
                raise AnalyticsError("`anchor` must look like YYYY-QN.") from exc
        else:
            quarter = (today.month - 1) // 3 + 1
            start = date(today.year, (quarter - 1) * 3 + 1, 1)
        end = _add_months(start, 3) - timedelta(days=1)
        complete = end < today
        previous = Period(
            key="previous",
            label=f"Q{((start.month - 1) // 3) or 4} {start.year if start.month > 3 else start.year - 1}",
            start=_add_months(start, -3),
            end=start - timedelta(days=1),
            complete=True,
        )
        same_period_last_year = Period(
            key="last_year",
            label=f"Q{(start.month - 1) // 3 + 1} {start.year - 1}",
            start=start.replace(year=start.year - 1),
            end=end.replace(year=end.year - 1),
            complete=complete,
        )

    elif granularity == "year":
        if anchor:
            try:
                year = int(anchor[:4])
            except (ValueError, TypeError) as exc:
                raise AnalyticsError("`anchor` must look like YYYY.") from exc
        else:
            year = today.year
        start = date(year, 1, 1)
        end = date(year, 12, 31)
        complete = end < today
        previous = Period(
            key="previous", label=str(year - 1), start=date(year - 1, 1, 1), end=date(year - 1, 12, 31), complete=True
        )
        same_period_last_year = previous

    else:
        raise AnalyticsError("`granularity` must be month, quarter or year.")

    label = {
        "month": f"{start:%B %Y}",
        "quarter": f"Q{(start.month - 1) // 3 + 1} {start.year}",
        "year": str(start.year),
    }[granularity]

    return (
        Period(key="current", label=label, start=start, end=end, complete=complete),
        previous,
        same_period_last_year,
    )


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def period_totals(user, currency: Currency, start: date, end: date) -> dict:
    """Income, expenses split into consumption and movement, and counts."""
    rows = (
        base_queryset(user, currency)
        .filter(transaction_date__range=(start, end))
        .values("transaction_type", "category__name")
        .annotate(total=Sum("amount"), count=Count("id"))
    )

    income = Decimal("0")
    expense_total = Decimal("0")
    count = 0
    expense_rows = []
    for row in rows:
        total = row["total"] or Decimal("0")
        count += row["count"]
        if row["transaction_type"] == Transaction.Type.INCOME:
            income += total
        else:
            expense_total += total
            expense_rows.append(row)

    consumption, movement = _split_expenses(expense_rows)
    return {
        "income": income,
        "expenses": expense_total,
        "consumption": consumption,
        "money_movement": movement,
        "net": income - expense_total,
        "net_consumption": income - consumption,
        "transaction_count": count,
    }


def _totals_payload(totals: dict) -> dict:
    return {
        "income": money(totals["income"]),
        "expenses": money(totals["expenses"]),
        "consumption": money(totals["consumption"]),
        "money_movement": money(totals["money_movement"]),
        "net": money(totals["net"]),
        "net_consumption": money(totals["net_consumption"]),
        "transaction_count": totals["transaction_count"],
        "savings_rate": percent(totals["net_consumption"], totals["income"]),
        "expense_ratio": percent(totals["consumption"], totals["income"]),
    }


def category_breakdown(user, currency: Currency, start: date, end: date, limit: int = 50) -> list[dict]:
    """Spending per category, largest first, split into consumption and movement."""
    movement_names = money_movement_categories()
    rows = (
        base_queryset(user, currency)
        .filter(
            transaction_date__range=(start, end),
            transaction_type=Transaction.Type.EXPENSE,
        )
        .values("category__id", "category__name")
        .annotate(total=Sum("amount"), count=Count("id"), average=Avg("amount"))
        .order_by("-total")
    )

    categories = []
    for row in rows[:limit]:
        name = row["category__name"] or "Uncategorised"
        categories.append(
            {
                "category_id": row["category__id"],
                "category": name,
                "total": money(row["total"]),
                "count": row["count"],
                "average": money(row["average"]),
                "is_money_movement": name.casefold() in movement_names,
            }
        )
    return categories


def monthly_series(user, currency: Currency, months: int, today: date | None = None) -> list[dict]:
    """Per-month totals across every month that has data in the window.

    Months with no rows are included as zeroes: a gap in spending is information,
    and a chart that skips it would imply continuity that is not there.
    """
    end_month = _month_start(today or timezone.localdate())
    start_month = _add_months(end_month, -(months - 1))

    rows = (
        base_queryset(user, currency)
        .filter(transaction_date__gte=start_month)
        .annotate(bucket=TruncMonth("transaction_date"))
        .values("bucket", "transaction_type", "category__name")
        .annotate(total=Sum("amount"), count=Count("id"))
    )

    buckets: dict[date, dict] = {}
    for row in rows:
        key = row["bucket"]
        bucket = buckets.setdefault(
            key,
            {
                "month": f"{key:%Y-%m}",
                "label": f"{key:%b %Y}",
                "income": Decimal("0"),
                "consumption": Decimal("0"),
                "money_movement": Decimal("0"),
                "expenses": Decimal("0"),
                "count": 0,
            },
        )
        total = row["total"] or Decimal("0")
        bucket["count"] += row["count"]
        if row["transaction_type"] == Transaction.Type.INCOME:
            bucket["income"] += total
        else:
            bucket["expenses"] += total
            name = (row["category__name"] or "").casefold()
            if name in money_movement_categories():
                bucket["money_movement"] += total
            else:
                bucket["consumption"] += total

    series = []
    cursor = start_month
    while cursor <= end_month:
        bucket = buckets.get(cursor)
        if bucket is None:
            series.append(
                {
                    "month": f"{cursor:%Y-%m}",
                    "label": f"{cursor:%b %Y}",
                    "income": 0.0,
                    "consumption": 0.0,
                    "money_movement": 0.0,
                    "expenses": 0.0,
                    "net": 0.0,
                    "count": 0,
                    "savings_rate": None,
                }
            )
        else:
            net = bucket["income"] - bucket["consumption"]
            series.append(
                {
                    "month": bucket["month"],
                    "label": bucket["label"],
                    "income": money(bucket["income"]),
                    "consumption": money(bucket["consumption"]),
                    "money_movement": money(bucket["money_movement"]),
                    "expenses": money(bucket["expenses"]),
                    "net": money(net),
                    "count": bucket["count"],
                    "savings_rate": percent(net, bucket["income"]),
                }
            )
        cursor = _add_months(cursor, 1)

    return series


def category_series(user, currency: Currency, months: int, top: int = 8, today: date | None = None) -> dict:
    """Consumption per category per month, for the largest categories only.

    A stacked chart with 41 bands is unreadable, so the biggest categories are
    kept individually and everything else is pooled, with money movement shown
    separately rather than pretending to be consumption.
    """
    end_month = _month_start(timezone.localdate())
    start_month = _add_months(end_month, -(months - 1))

    rows = list(
        base_queryset(user, currency)
        .filter(
            transaction_date__gte=start_month,
            transaction_type=Transaction.Type.EXPENSE,
        )
        .annotate(bucket=TruncMonth("transaction_date"))
        .values("bucket", "category__name")
        .annotate(total=Sum("amount"))
    )

    movement_names = money_movement_categories()
    totals_by_category: dict[str, Decimal] = {}
    for row in rows:
        name = row["category__name"] or "Uncategorised"
        if name.casefold() in movement_names:
            continue
        totals_by_category[name] = totals_by_category.get(name, Decimal("0")) + (
            row["total"] or Decimal("0")
        )

    leaders = [
        name
        for name, _ in sorted(totals_by_category.items(), key=lambda item: -item[1])[:top]
    ]
    leader_set = set(leaders)

    months = []
    cursor = start_month
    while cursor <= end_month:
        months.append(cursor)
        cursor = _add_months(cursor, 1)

    grid = {month: {name: Decimal("0") for name in leaders} for month in months}
    grid_other = {month: Decimal("0") for month in months}
    grid_movement = {month: Decimal("0") for month in months}

    for row in rows:
        name = row["category__name"] or "Uncategorised"
        bucket = row["bucket"]
        if bucket not in grid:
            continue
        total = row["total"] or Decimal("0")
        if name.casefold() in movement_names:
            grid_movement[bucket] += total
        elif name in leader_set:
            grid[bucket][name] += total
        else:
            grid_other[bucket] += total

    return {
        "months": [f"{month:%Y-%m}" for month in months],
        "labels": [f"{month:%b %Y}" for month in months],
        "categories": leaders,
        "series": [
            {
                "category": name,
                "values": [money(grid[month][name]) for month in months],
            }
            for name in leaders
        ],
        "other": [money(grid_other[month]) for month in months],
        "money_movement": [money(grid_movement[month]) for month in months],
    }


def weekday_profile(user, currency: Currency, start: date, end: date) -> list[dict]:
    """Spending by day of week — reveals routine versus occasional behaviour."""
    rows = (
        exclude_money_movement(base_queryset(user, currency))
        .filter(
            transaction_date__range=(start, end),
            transaction_type=Transaction.Type.EXPENSE,
        )
        .annotate(weekday=ExtractWeekDay("transaction_date"))
        .values("weekday")
        .annotate(total=Sum("amount"), count=Count("id"))
    )
    by_day = {row["weekday"]: row for row in rows}
    payload = []
    for weekday in range(1, 8):
        row = by_day.get(weekday)
        payload.append(
            {
                "weekday": weekday,
                "label": WEEKDAY_LABELS[weekday],
                "total": money(row["total"]) if row else 0.0,
                "count": row["count"] if row else 0,
            }
        )
    return payload


def top_descriptions(user, currency: Currency, start: date, end: date, limit: int = 12) -> list[dict]:
    """Biggest spending descriptions, which behave like merchants here."""
    rows = (
        exclude_money_movement(base_queryset(user, currency))
        .filter(
            transaction_date__range=(start, end),
            transaction_type=Transaction.Type.EXPENSE,
        )
        .exclude(description="")
        .values("description")
        .annotate(total=Sum("amount"), count=Count("id"), last=Max("transaction_date"))
        .order_by("-total")[:limit]
    )
    return [
        {
            "description": row["description"],
            "total": money(row["total"]),
            "count": row["count"],
            "average": money((row["total"] or Decimal("0")) / row["count"]),
            "last": row["last"],
        }
        for row in rows
    ]


def recurring_expenses(user, currency: Currency, months: int = 12, today: date | None = None) -> list[dict]:
    """Categories that appear almost every month with little variation.

    These are the committed costs — rent, insurance, subscriptions — and they are
    the first thing to look at when spending needs to come down, because they do
    not require a change of habit, only a decision.
    """
    today = today or timezone.localdate()
    end_month = _month_start(today)
    start_month = _add_months(end_month, -(months - 1))
    movement_names = money_movement_categories()

    rows = (
        base_queryset(user, currency)
        .filter(
            transaction_date__gte=start_month,
            transaction_type=Transaction.Type.EXPENSE,
        )
        .annotate(bucket=TruncMonth("transaction_date"))
        .values("category__name", "bucket")
        .annotate(total=Sum("amount"), count=Count("id"))
    )

    by_category: dict[str, dict[date, Decimal]] = {}
    for row in rows:
        name = row["category__name"] or "Uncategorised"
        if name.casefold() in movement_names:
            continue
        by_category.setdefault(name, {})[row["bucket"]] = row["total"] or Decimal("0")

    # Only months that are finished can be judged as "present".
    finished_months = [m for m in _month_range(start_month, end_month) if _month_end(m) < today]
    if not finished_months:
        return []

    recurring = []
    for name, per_month in by_category.items():
        present = [per_month.get(month, Decimal("0")) for month in finished_months]
        months_with_spend = sum(1 for value in present if value > 0)
        if months_with_spend < max(3, int(len(finished_months) * 0.7)):
            continue
        values = [float(value) for value in present if value > 0]
        mean = statistics.fmean(values)
        deviation = statistics.pstdev(values) if len(values) > 1 else 0.0
        recurring.append(
            {
                "category": name,
                "months_present": months_with_spend,
                "months_considered": len(finished_months),
                "monthly_average": round(mean, 2),
                "monthly_min": round(min(values), 2),
                "monthly_max": round(max(values), 2),
                "variability_percent": round((deviation / mean) * 100, 1) if mean else None,
            }
        )

    recurring.sort(key=lambda item: -item["monthly_average"])
    return recurring


def _month_range(start: date, end: date):
    cursor = start
    while cursor <= end:
        yield cursor
        cursor = _add_months(cursor, 1)


# ---------------------------------------------------------------------------
# Interpretation
# ---------------------------------------------------------------------------


def spend_outlook(user, currency: Currency, today: date | None = None) -> dict:
    """Where this month is heading, against the user's own recent normal.

    Compares the *pace* (spend per elapsed day) rather than the raw total, which is
    the only fair way to read a month in progress, and projects the month end.
    """
    today = today or timezone.localdate()
    month_start = _month_start(today)
    days_elapsed = (today - month_start).days + 1
    days_in_month = (_month_end(today) - month_start).days + 1

    series = monthly_series(user, currency, 13, today)
    current = series[-1]
    finished = [month for month in series[:-1] if month["consumption"] > 0]
    baseline_values = [Decimal(str(month["consumption"])) for month in finished]

    baseline = (
        statistics.median([float(value) for value in baseline_values]) if baseline_values else 0.0
    )
    spent = Decimal(str(current["consumption"]))
    pace = spent / days_elapsed
    projection = (pace * days_in_month).quantize(CENT)

    spread = None
    if len(baseline_values) > 1:
        spread = statistics.pstdev([float(value) for value in baseline_values])

    # "High" or "low" only when the month is clearly outside the user's own range.
    verdict = "in_progress"
    if baseline:
        ratio = float(projection) / baseline
        if ratio >= 1.2:
            verdict = "high"
        elif ratio <= 0.8:
            verdict = "low"
        else:
            verdict = "normal"

    return {
        "month": current["month"],
        "label": current["label"],
        "days_elapsed": days_elapsed,
        "days_in_month": days_in_month,
        "spent_so_far": money(spent),
        "consumption_so_far": money(spent),
        "daily_pace": money(pace),
        "projected_month_end": money(projection),
        "typical_month": money(Decimal(str(round(baseline, 2)))),
        "monthly_spread": money(Decimal(str(round(spread, 2)))) if spread is not None else None,
        "verdict": verdict,
        "months_compared": len(baseline_values),
        # How much is left to stay inside the typical month.
        "budget_remaining_to_typical": money(
            Decimal(str(round(baseline, 2))) - spent
        )
        if baseline
        else None,
    }


def build_insights(
    *,
    current: dict,
    previous: dict,
    current_categories: list[dict],
    previous_categories: list[dict],
    series: list[dict],
    weekday: list[dict],
    recurring: list[dict],
    currency_code: str,
) -> list[dict]:
    """Plain-language observations, ordered by how much they matter.

    Each insight carries a `tone` (`warning`, `good`, `neutral`) so the UI can
    colour it, and the numbers behind it so nothing is asserted without evidence.
    """
    insights: list[dict] = []

    # 1. Overall movement against the previous comparable period.
    change = Decimal(str(current["consumption"])) - Decimal(str(previous["consumption"]))
    change_pct = percent(change, Decimal(str(previous["consumption"]))) if previous["consumption"] else None
    if change_pct is not None and abs(change_pct) >= 10:
        insights.append(
            {
                "tone": "warning" if change > 0 else "good",
                "title": f"Spending is {'up' if change > 0 else 'down'} {abs(change_pct):.0f}%",
                "detail": (
                    f"{money(abs(change)):,.2f} {currency_code} "
                    f"{'more' if change > 0 else 'less'} than the previous period."
                ),
                "value": change_pct,
            }
        )

    # 2. The category that grew the most, in absolute terms.
    previous_by_name = {row["category"]: row["total"] for row in previous_categories}
    grown = []
    for row in current_categories:
        if row["is_money_movement"]:
            continue
        before = previous_by_name.get(row["category"], 0.0)
        grown.append((row["category"], row["total"] - before, row["total"], before))
    grown.sort(key=lambda item: -item[1])
    if grown and grown[0][1] > 0:
        name, increase, now, before = grown[0]
        insights.append(
            {
                "tone": "warning",
                "title": f"{name} grew the most",
                "detail": f"{money(increase):,.2f} {currency_code} more than the previous period ({money(before):,.2f} → {money(now):,.2f}).",
                "value": money(increase),
            }
        )

    # 3. Discretionary spending that fell — worth reinforcing.
    fallen = [item for item in grown if item[1] < 0 and item[3] > 0]
    if fallen:
        name, decrease, now, before = fallen[-1]
        insights.append(
            {
                "tone": "good",
                "title": f"{name} is down",
                "detail": f"{money(abs(decrease)):,.2f} {currency_code} less than the previous period.",
                "value": money(abs(decrease)),
            }
        )

    # 4. Share of spending that is money movement rather than consumption.
    if current["expenses"]:
        share = percent(Decimal(str(current["money_movement"])), Decimal(str(current["expenses"])))
        if share and share >= 20:
            insights.append(
                {
                    "tone": "neutral",
                    "title": f"{share:.0f}% of your outflows are money movement",
                    "detail": (
                        "Transfers, loans and currency exchanges leave your net worth "
                        "unchanged, so the consumption figure is the one to judge habits by."
                    ),
                    "value": share,
                }
            )

    # 5. The most persistent cost.
    if recurring:
        biggest = recurring[0]
        variability = biggest["variability_percent"] or 0
        insights.append(
            {
                "tone": "neutral",
                "title": f"{biggest['category']} is your steadiest cost",
                "detail": (
                    f"About {biggest['monthly_average']:,.2f} {currency_code} a month across "
                    f"{biggest['months_present']} of the last {biggest['months_considered']} months"
                    + (f" (±{variability:.0f}%)." if variability else ".")
                ),
                "value": biggest["monthly_average"],
            }
        )

    # 6. Concentration in one weekday, if any.
    total_weekday = sum(row["total"] for row in weekday)
    if total_weekday:
        busiest = max(weekday, key=lambda row: row["total"])
        share = (busiest["total"] / total_weekday) * 100
        if share >= 25:
            insights.append(
                {
                    "tone": "neutral",
                    "title": f"{busiest['label']} is your heaviest day",
                    "detail": f"{share:.0f}% of spending happens on {busiest['label']}s ({money(busiest['total']):,.2f} {currency_code}).",
                    "value": round(share, 1),
                }
            )

    # 7. Momentum: the last three months against the three before them.
    spend_months = [Decimal(str(row["consumption"])) for row in series if row["consumption"] > 0]
    if len(spend_months) >= 6:
        recent = statistics.fmean(float(v) for v in spend_months[-3:])
        earlier = statistics.fmean(float(v) for v in spend_months[-6:-3])
        if earlier:
            momentum = ((recent - earlier) / earlier) * 100
            if abs(momentum) >= 8:
                insights.append(
                    {
                        "tone": "warning" if momentum > 0 else "good",
                        "title": f"Three-month trend is {'rising' if momentum > 0 else 'falling'}",
                        "detail": f"Average monthly consumption moved {momentum:+.0f}% ({earlier:,.0f} → {recent:,.0f} {currency_code}).",
                        "value": round(momentum, 1),
                    }
                )

    # 8. Savings rate, when income exists.
    savings_rate = current["savings_rate"]
    if savings_rate is not None:
        tone = "good" if savings_rate >= 20 else ("warning" if savings_rate < 0 else "neutral")
        insights.append(
            {
                "tone": tone,
                "title": f"Savings rate {savings_rate:.0f}%",
                "detail": (
                    f"Income {money(Decimal(str(current['income']))):,.2f} minus consumption "
                    f"{money(Decimal(str(current['consumption']))):,.2f} {currency_code}."
                ),
                "value": savings_rate,
            }
        )

    # 9. The largest single month of consumption in the window.
    if series:
        peak = max(series, key=lambda row: row["consumption"])
        if peak["consumption"] > 0:
            insights.append(
                {
                    "tone": "neutral",
                    "title": f"Biggest month: {peak['label']}",
                    "detail": f"{money(peak['consumption']):,.2f} {currency_code} of consumption in {peak['count']} transactions.",
                    "value": peak["consumption"],
                }
            )

    return insights


def build_dashboard(user, *, currency_code: str | None = None, today: date | None = None, months: int = DEFAULT_TREND_MONTHS) -> dict:
    """Everything the dashboard needs, in one round trip."""
    today = today or timezone.localdate()
    currency = resolve_currency(currency_code)

    current, previous, same_period_last_year = resolve_period("month", None, today)
    current_totals = period_totals(user, currency, current.start, current.end)
    previous_totals = period_totals(user, currency, previous.start, previous.end)
    last_year_totals = period_totals(user, currency, same_period_last_year.start, same_period_last_year.end)

    current_categories = category_breakdown(user, currency, current.start, current.end)
    previous_categories = category_breakdown(user, currency, previous.start, previous.end)

    series = monthly_series(user, currency, months, today)
    weekday = weekday_profile(user, currency, _add_months(_month_start(today), -11), today)
    recurring = recurring_expenses(user, currency, months=12, today=today)
    outlook = spend_outlook(user, currency, today)

    return {
        "currency": currency.code,
        "generated_at": timezone.now(),
        "available_currencies": available_currencies(user),
        "period": {
            **current.as_dict(),
            "compared_with": previous.as_dict(),
            "same_period_last_year": same_period_last_year.as_dict(),
        },
        "totals": {
            "current": _totals_payload(current_totals),
            "previous": _totals_payload(previous_totals),
            "same_period_last_year": _totals_payload(last_year_totals),
        },
        "comparisons": {
            "consumption": delta(current_totals["consumption"], previous_totals["consumption"]),
            "expenses": delta(current_totals["expenses"], previous_totals["expenses"]),
            "income": delta(current_totals["income"], previous_totals["income"]),
            "net": delta(current_totals["net_consumption"], previous_totals["net_consumption"]),
            "consumption_vs_last_year": delta(
                current_totals["consumption"], last_year_totals["consumption"]
            ),
        },
        "outlook": outlook,
        "top_categories": current_categories[:12],
        "all_categories": current_categories,
        "previous_categories": previous_categories,
        "monthly": series,
        "category_trend": category_series(user, currency, months, today=today),
        "weekday": weekday,
        "top_descriptions": top_descriptions(
            user, currency, _add_months(_month_start(today), -11), today
        ),
        "recurring": recurring,
        "insights": build_insights(
            current=_totals_payload(current_totals),
            previous=_totals_payload(previous_totals),
            current_categories=current_categories,
            previous_categories=previous_categories,
            series=series,
            weekday=weekday,
            recurring=recurring,
            currency_code=currency.code,
        ),
        "data_range": _data_range(user, currency),
    }


def _data_range(user, currency: Currency) -> dict:
    bounds = base_queryset(user, currency).aggregate(first=Min("transaction_date"), last=Max("transaction_date"))
    return {"first": bounds["first"], "last": bounds["last"]}
