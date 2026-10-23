"""Querystring filtering for the transaction list.

The list endpoint is the busiest screen in the app, so filtering happens in the
database rather than in the browser: the user's ledger can be tens of thousands of
rows, and the client only ever holds one page.

`date_from` / `date_to` / `month` exist because `transaction_date` as an exact-match
filter is almost never what a person wants — "show me March" is the common case.
"""

import django_filters as filters
from django.db.models import Q, QuerySet
from rest_framework.filters import OrderingFilter

from .models import Transaction

#: Fallback tie-breakers. A ledger has many rows sharing a transaction date (an
#: import inserts hundreds for the same day), and without a total order the database
#: is free to return those rows in any sequence — which breaks pagination.
_TIEBREAKERS = ("-created_date", "-id")


class TransactionOrderingFilter(OrderingFilter):
    """Deterministic ordering that keeps same-day rows stable.

    ``ordering=-transaction_date`` means exactly what the UI label says: the newest
    calendar date first. It is **not** grouped by month, and insertion order never
    overrides the transaction date — a row dated 13/10 sorts above one dated 09/10
    even if the latter was typed more recently. "Most recently entered first"
    regardless of date is a separate sort (``-created_date,-id``).

    The tie-breakers only decide rows that share the same date (or the same value of
    whatever field is being sorted), so a page boundary never repeats or drops a row.

    This has to be an `OrderingFilter`, not a FilterSet method: DRF evaluates
    `filterset_class` **before** the ordering backend, so a FilterSet sees an empty
    `order_by` and has nothing to extend.
    """

    def filter_queryset(self, request, queryset: QuerySet, view) -> QuerySet:
        queryset = super().filter_queryset(request, queryset, view)

        order_by = list(queryset.query.order_by or ())
        names = [str(term).lstrip("-") for term in order_by]

        if names:
            missing = [field for field in _TIEBREAKERS if field.lstrip("-") not in names]
            if missing:
                return queryset.order_by(*order_by, *missing)

        return queryset


class TransactionFilter(filters.FilterSet):
    """Filters accepted by `GET /api/v1/transactions/`."""

    #: `?account=7` — everything that moves money on that account, **including
    #: incoming transfers**. A transfer is one row whose `account` is the source, so
    #: an exact-match filter would hide the credit from the destination's history.
    account = filters.NumberFilter(method="filter_account")
    #: `?destination_account=7` — only the incoming side of transfers.
    destination_account = filters.NumberFilter(field_name="destination_account")
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
            "destination_account",
            "category",
            "budget",
            "transaction_type",
            "transaction_date",
        ]

    def filter_account(self, queryset, name, value):
        """Both sides of a transfer: the source account and the destination.

        `destination_account` is null on income/expense rows, so this only widens
        the result for transfers — no other transaction type can match by accident.
        """
        return queryset.filter(Q(account=value) | Q(destination_account=value))

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
