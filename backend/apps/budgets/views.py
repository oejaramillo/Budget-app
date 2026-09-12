from django.db.models import Q, Sum
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.transactions.models import Transaction

from .models import Budget
from .serializers import BudgetSerializer


class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    filterset_fields = ["is_active", "currency", "start_date", "end_date"]
    search_fields = ["name"]
    ordering_fields = ["start_date", "end_date", "max_amount", "name"]

    def get_queryset(self):
        # `spent_amount` is annotated so the serializer never triggers an extra
        # query per budget row.
        return (
            Budget.objects.filter(user=self.request.user)
            .select_related("currency")
            .prefetch_related("accounts")
            .annotate(
                spent_amount=Sum(
                    "transactions__amount",
                    filter=Q(transactions__transaction_type=Transaction.Type.EXPENSE),
                )
            )
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get"], url_path="status")
    def status(self, request):
        """Progress of each active budget: limit, spent, remaining, percentage."""
        rows = []
        for budget in self.get_queryset().filter(is_active=True):
            spent = budget.spent_amount or 0
            limit = budget.max_amount
            percentage = float((spent / limit) * 100) if limit else 0.0
            rows.append(
                {
                    "id": budget.pk,
                    "name": budget.name,
                    "currency": budget.currency.code,
                    "start_date": budget.start_date,
                    "end_date": budget.end_date,
                    "max_amount": limit,
                    "spent_amount": spent,
                    "remaining_amount": limit - spent,
                    "percentage_used": round(percentage, 2),
                    "is_over_budget": spent > limit,
                }
            )
        return Response(rows)
