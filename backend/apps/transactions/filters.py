"""Querystring filtering for the transaction list.

The list endpoint is the busiest screen in the app, so filtering happens in the
database rather than in the browser: the user's ledger can be tens of thousands of
rows, and the client only ever holds one page.

`date_from` / `date_to` / `month` exist because `transaction_date` as an exact-match
filter is almost never what a person wants — "show me March" is the common case.
"""

import django_filters as filters
from django.db.models import F, QuerySet
from django.db.models.functions import TruncMonth
from rest_framework.filters import OrderingFilter

from .models import Transaction

#: Fallback tie-breakers when a caller sorts by something other than the month.
_TIEBREAKERS = ("-created_date", "-id")

#: Annotation holding the month (`2026-09-01`) a transaction belongs to.
MONTH_FIELD = "date_month"


class TransactionOrderingFilter(OrderingFilter):
    """Ordering that matches how a ledger is actually read.

    **Newest month first, and within a month the most recently entered first.**

    * Month-first keeps the record chronological, so an imported batch and the rows
      entered by hand for the same period sit together instead of being interleaved
      by the order they happened to be typed in.
    * Newest-entered-first *inside* a month is what makes the screen usable while
      logging: entries added now lead a batch imported earlier for the same month.

    This has to be an `OrderingFilter`, not a FilterSet method: DRF evaluates
    `filterset_class` **before** the ordering backend, so a FilterSet sees an empty
    `order_by` and has nothing to translate. Any other sort field is passed straight
    through to the default implementation.
    """

    def filter_queryset(self, request, queryset: QuerySet, view) -> QuerySet:
        queryset = super().filter_queryset(request, queryset, view)

        order_by = list(queryset.query.order_by or ())
        names = [str(term).lstrip("-") for term in order_by]

        if names and names[0] == "transaction_date":
            # `TruncMonth` on a DateField is a plain calendar truncation: no timezone
            # conversion, so a stored date keeps its day.
            return queryset.annotate(**{MONTH_FIELD: TruncMonth("transaction_date")}).order_by(
                f"-{MONTH_FIELD}", "-created_date", "-id"
            )

        if names:
            missing = [field for field in _TIEBREAKERS if field.lstrip("-") not in names]
            if missing:
                return queryset.order_by(*order_by, *missing)

        return queryset


class TransactionFilter(filters.FilterSet):
    """Filters accepted by `GET /api/v1/transactions/`."""

    date_from = filters.DateFilter(field_name="transaction_date", lookup_expr="gte")
    date_to = filters.DateFilter(field_name="transaction_date", lookup_expr="lte")
    amount_min = filters.NumberFilter(field_name="amount", lookup_expr="gte")
    amount_max = filters.NumberFilter(field_name="amount", lookup_expr="lte")
    #: `?month=2026-03` — the shorthand the UI uses for its period presets.
    month = filters.CharFilter(method="filter_month")
    #: `?uncategorised=true` — the "needs tidying" list.
    uncategorised = filters.BooleanFilter(
        field_name="category", lookup_expr="isnull", label="Uncategorised only"
    )

    class Meta:
        model = Transaction
        fields = [
            "account",
            "destination_account",
            "category",
            "budget",
            "transaction_type",
            "transaction_date",
        ]

    def filter_month(self, queryset, name, value):
        """Filter to a single `YYYY-MM` period."""
        parts = str(value).split("-")
        if len(parts) < 2:
            return queryset.none()
        try:
            year, month = int(parts[0]), int(parts[1])
            if not 1 <= month <= 12:
                return queryset.none()
        except ValueError:
            return queryset.none()
        return queryset.filter(
            transaction_date__year=year, transaction_date__month=month
        )
