from datetime import date

from django.db import transaction as db_transaction
from django.db.models import Count, Max, Min, Sum
from django.db.models.functions import TruncMonth
from django.utils.dateparse import parse_date
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.currencies.models import Currency

from .filters import TransactionFilter, TransactionOrderingFilter
from .models import Category, Transaction
from .serializers import CategorySerializer, TransactionSerializer
from .services import create_transaction, delete_transaction, update_transaction


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    filterset_fields = ["budget", "is_active"]
    search_fields = ["name"]
    ordering_fields = ["name"]

    def get_queryset(self):
        return (
            Category.objects.filter(user=self.request.user)
            .select_related("budget")
            .annotate(transaction_count=Count("transactions"))
            .order_by("name")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TransactionViewSet(viewsets.ModelViewSet):
    """CRUD for transactions with a per-user queryset and balance side effects."""

    serializer_class = TransactionSerializer
    filterset_class = TransactionFilter
    # Listed after the project defaults so the ledger-specific ordering wins.
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        TransactionOrderingFilter,
    ]
    search_fields = ["description", "account__name", "category__name"]
    # `created_date` is offered so the screen can order by "most recently entered",
    # which is not the same as "newest transaction date": a batch entered today for
    # last month would otherwise be buried.
    ordering_fields = ["transaction_date", "amount", "created_date", "id"]

    def get_queryset(self):
        return (
            Transaction.objects.filter(user=self.request.user)
            .select_related("account", "destination_account", "category", "budget", "currency")
        )

    def perform_create(self, serializer):
        serializer.instance = create_transaction(self.request.user, serializer.validated_data)

    def perform_update(self, serializer):
        serializer.instance = update_transaction(serializer.instance, serializer.validated_data)

    def perform_destroy(self, instance):
        delete_transaction(instance)

    # -- Reporting -----------------------------------------------------------

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """Income, expenses, net and per-category breakdown for a date range.

        Query parameters: `start`, `end` (YYYY-MM-DD, both optional, defaulting to
        the current month) and `target` (currency code to convert into).
        """
        today = date.today()
        start = parse_date(request.query_params.get("start", "")) or today.replace(day=1)
        end = parse_date(request.query_params.get("end", "")) or today

        if end < start:
            raise ValidationError({"end": "End date must be on or after the start date."})

        target_code = request.query_params.get("target")
        target = None
        if target_code:
            target = Currency.objects.filter(code=target_code.upper()).first()
            if target is None:
                raise ValidationError({"target": f"Unknown currency '{target_code}'."})

        rows = (
            self.get_queryset()
            .filter(transaction_date__range=(start, end))
            .values("transaction_type", "currency__code")
            .annotate(total=Sum("amount"), count=Count("id"))
        )

        total_income = 0
        total_expenses = 0
        count = 0
        for row in rows:
            amount = row["total"] or 0
            count += row["count"]
            if target is not None:
                source = Currency.objects.filter(code=row["currency__code"]).first()
                if source is not None:
                    amount = source.convert_to(amount, target)
            if row["transaction_type"] == Transaction.Type.INCOME:
                total_income += amount
            elif row["transaction_type"] == Transaction.Type.EXPENSE:
                total_expenses += amount

        by_category = list(
            self.get_queryset()
            .filter(transaction_date__range=(start, end), transaction_type=Transaction.Type.EXPENSE)
            .values("category__id", "category__name", "currency__code")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-total")[:20]
        )

        return Response(
            {
                "period_start": start,
                "period_end": end,
                "currency": target.code if target else None,
                "total_income": total_income,
                "total_expenses": total_expenses,
                "net": total_income - total_expenses,
                "transaction_count": count,
                "by_category": [
                    {
                        "category_id": row["category__id"],
                        "category_name": row["category__name"] or "Uncategorised",
                        "currency": row["currency__code"],
                        "total": row["total"],
                        "count": row["count"],
                    }
                    for row in by_category
                ],
            }
        )

    @action(detail=False, methods=["get"], url_path="monthly")
    def monthly(self, request):
        """Income/expense totals grouped by month for the last N months."""
        try:
            months = int(request.query_params.get("months", 6))
        except (TypeError, ValueError):
            raise ValidationError({"months": "Must be an integer."})
        months = max(1, min(months, 36))

        rows = (
            self.get_queryset()
            .annotate(month=TruncMonth("transaction_date"))
            .values("month", "transaction_type")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-month")
        )

        buckets: dict[str, dict] = {}
        for row in rows:
            key = row["month"].strftime("%Y-%m")
            bucket = buckets.setdefault(
                key, {"month": key, "income": 0, "expenses": 0, "net": 0, "count": 0}
            )
            bucket["count"] += row["count"]
            if row["transaction_type"] == Transaction.Type.INCOME:
                bucket["income"] += row["total"] or 0
            elif row["transaction_type"] == Transaction.Type.EXPENSE:
                bucket["expenses"] += row["total"] or 0
            bucket["net"] = bucket["income"] - bucket["expenses"]

        ordered = sorted(buckets.values(), key=lambda b: b["month"], reverse=True)[:months]
        return Response(ordered)

    @action(detail=False, methods=["get"], url_path="descriptions")
    def descriptions(self, request):
        """Distinct descriptions the user has typed before, most used first.

        This is what powers autocomplete in the logging form. Paying a
        merchant/description twice is the norm, so repeating a previous entry with
        one keystroke is the difference between a form you tolerate and one you use.

        Query parameters:
            `q`       case-insensitive substring filter (the text typed so far)
            `account` restrict to descriptions used on one account
            `limit`   maximum suggestions returned (default 20, max 100)
        """
        try:
            limit = int(request.query_params.get("limit", 20))
        except (TypeError, ValueError):
            raise ValidationError({"limit": "Must be an integer."})
        limit = max(1, min(limit, 100))

        queryset = self.get_queryset().exclude(description="")
        account = request.query_params.get("account")
        if account:
            queryset = queryset.filter(account_id=account)

        term = (request.query_params.get("q") or "").strip()
        if term:
            queryset = queryset.filter(description__icontains=term)

        rows = (
            queryset.values("description")
            .annotate(uses=Count("id"), last_used=Max("transaction_date"))
            .order_by("-uses", "-last_used")
        )
        # Slicing after ordering keeps the aggregate on the database and the
        # payload small; the limit is already clamped above.
        payload = [
            {
                "description": row["description"],
                "uses": row["uses"],
                "last_used": row["last_used"],
            }
            for row in rows[:limit]
        ]
        return Response(payload)

    @action(detail=False, methods=["get"], url_path="recent")
    def recent(self, request):
        """The user's most recent transactions, newest first.

        Used by the "repeat a recent entry" affordance in the logging form. Mirrors
        the list endpoint but ignores filters and always returns a small page.
        """
        try:
            limit = int(request.query_params.get("limit", 8))
        except (TypeError, ValueError):
            raise ValidationError({"limit": "Must be an integer."})
        limit = max(1, min(limit, 25))

        queryset = self.get_queryset().order_by("-transaction_date", "-created_date")[:limit]
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        """A few facts about the user's ledger, for the logging screen header.

        Deliberately small: the point is to orient the user ("4,441 entries, back to
        December 2018, 3,796 to categorise"), not to duplicate the reporting
        endpoints.
        """
        queryset = self.get_queryset()
        bounds = queryset.aggregate(first=Min("transaction_date"), last=Max("transaction_date"))
        return Response(
            {
                "count": queryset.count(),
                "first_date": bounds["first"],
                "last_date": bounds["last"],
                "uncategorised": queryset.filter(category__isnull=True).count(),
                "without_description": queryset.filter(description="").count(),
            }
        )

    @action(detail=False, methods=["post"], url_path="bulk")
    def bulk_create(self, request):
        """Create several transactions atomically (fast daily entry).

        Every item is validated before anything is written, so either the whole
        batch lands or none of it does.
        """
        if not isinstance(request.data, list):
            raise ValidationError({"detail": "Expected a JSON array of transactions."})
        if not request.data:
            raise ValidationError({"detail": "The array is empty."})
        if len(request.data) > 100:
            raise ValidationError({"detail": "At most 100 transactions per request."})

        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        created = []
        with db_transaction.atomic():
            for item in serializer.validated_data:
                created.append(create_transaction(request.user, item))

        return Response(self.get_serializer(created, many=True).data, status=201)
