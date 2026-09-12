from datetime import date

from django.db import transaction as db_transaction
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils.dateparse import parse_date
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.currencies.models import Currency

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


class TransactionViewSet(viewsets.ModelViewSet):

    serializer_class = TransactionSerializer
    filterset_fields = [
        "account",
        "destination_account",
        "category",
        "budget",
        "transaction_type",
        "transaction_date",
    ]
    search_fields = ["description", "account__name", "category__name"]
    ordering_fields = ["transaction_date", "amount", "created_date"]

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
