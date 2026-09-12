from datetime import date
from decimal import Decimal

from django.db.models import Prefetch, Sum
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.currencies.models import Currency

from .models import Holding, Valuation
from .serializers import HoldingSerializer, ValuationSerializer


class HoldingViewSet(viewsets.ModelViewSet):
    serializer_class = HoldingSerializer
    filterset_fields = ["kind", "currency", "account"]
    search_fields = ["symbol", "name"]
    ordering_fields = ["symbol", "cost_basis", "created_date"]

    def get_queryset(self):
        return (
            Holding.objects.filter(user=self.request.user)
            .select_related("currency", "account")
            .prefetch_related(
                Prefetch("valuations", queryset=Valuation.objects.order_by("-valued_on"))
            )
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get"], url_path="portfolio")
    def portfolio(self, request):
        """Portfolio totals, optionally converted into `?target=CODE`."""
        target_code = request.query_params.get("target")
        target = None
        if target_code:
            target = Currency.objects.filter(code=target_code.upper()).first()
            if target is None:
                raise ValidationError({"target": f"Unknown currency '{target_code}'."})

        total_value = Decimal("0.00")
        total_cost = Decimal("0.00")
        by_kind: dict[str, dict] = {}
        positions = []

        for holding in self.get_queryset():
            value = holding.market_value
            cost = holding.cost_basis
            if target is not None:
                value = holding.currency.convert_to(value, target)
                cost = holding.currency.convert_to(cost, target)
            total_value += value
            total_cost += cost

            bucket = by_kind.setdefault(
                holding.kind, {"kind": holding.kind, "value": Decimal("0.00"), "cost": Decimal("0.00"), "count": 0}
            )
            bucket["value"] += value
            bucket["cost"] += cost
            bucket["count"] += 1

            positions.append(
                {
                    "id": holding.pk,
                    "symbol": holding.symbol,
                    "kind": holding.kind,
                    "currency": holding.currency.code,
                    "quantity": holding.quantity,
                    "market_value": value,
                    "cost_basis": cost,
                    "unrealised_gain": value - cost,
                }
            )

        gain = total_value - total_cost
        gain_percent = (
            ((gain / total_cost) * 100).quantize(Decimal("0.01")) if total_cost else Decimal("0.00")
        )

        return Response(
            {
                "target_currency": target.code if target else None,
                "total_market_value": total_value,
                "total_cost_basis": total_cost,
                "unrealised_gain": gain,
                "unrealised_gain_percent": gain_percent,
                "holding_count": len(positions),
                "by_kind": list(by_kind.values()),
                "positions": positions,
            }
        )

    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request):
        """Portfolio value over time, aggregated per valuation date."""
        rows = (
            Valuation.objects.filter(holding__user=request.user)
            .values("valued_on")
            .annotate(total=Sum("value"))
            .order_by("valued_on")
        )
        return Response(
            [{"date": row["valued_on"], "value": row["total"]} for row in rows]
        )


class ValuationViewSet(viewsets.ModelViewSet):
    serializer_class = ValuationSerializer
    filterset_fields = ["holding", "valued_on"]
    ordering_fields = ["valued_on", "value"]

    def get_queryset(self):
        return Valuation.objects.filter(holding__user=self.request.user).select_related(
            "holding"
        )
