from decimal import Decimal

from django.db.models import Count, Sum
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import Account

from .models import Currency
from .serializers import CurrencySerializer, CurrencySummarySerializer


class CurrencyViewSet(viewsets.ModelViewSet):
    """Currency catalogue.

    Read access is open to any authenticated user because currencies are shared
    reference data. Creating, editing or refreshing rates is restricted to staff
    accounts: a regular user must not be able to rewrite the rates that other
    tenants' reports are built on.
    """

    serializer_class = CurrencySerializer
    queryset = Currency.objects.all()
    filterset_fields = ["code", "is_active", "principal"]
    search_fields = ["name", "code"]
    ordering_fields = ["code", "name", "exchange_rate"]

    def get_permissions(self):
        if self.action in {"list", "retrieve", "convert", "summary"}:
            return [IsAuthenticated()]
        return [IsAdminUser()]

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """Total balance per currency, optionally expressed in one currency.

        `?target=EUR` converts every balance using the stored cross rate. Without
        a target the raw per-currency totals are returned untouched, so nothing is
        silently converted.
        """
        target_code = request.query_params.get("target")
        target = None
        if target_code:
            target = Currency.objects.filter(
                code=target_code.upper(), is_active=True
            ).first()
            if target is None:
                raise ValidationError({"target": f"Unknown or inactive currency '{target_code}'."})

        rows = (
            Account.objects.filter(user=request.user)
            .values("currency__code", "currency__name")
            .annotate(total=Sum("balance"), accounts=Count("id"))
            .order_by("currency__code")
        )

        payload = []
        for row in rows:
            total = row["total"] or Decimal("0.00")
            converted = False
            rate = None
            code = row["currency__code"]
            if target is not None and code != target.code:
                source_currency = Currency.objects.filter(code=code).first()
                if source_currency is not None:
                    rate = Decimal(target.exchange_rate) / Decimal(
                        source_currency.exchange_rate
                    )
                    total = (total * rate).quantize(Decimal("0.01"))
                    converted = True
            payload.append(
                {
                    "currency_code": code,
                    "currency_name": row["currency__name"],
                    "total_balance": total,
                    "account_count": row["accounts"],
                    "converted": converted,
                    "conversion_rate": rate,
                }
            )

        serializer = CurrencySummarySerializer(payload, many=True)
        return Response(
            {
                "target_currency": target.code if target else None,
                "results": serializer.data,
            }
        )

    @action(detail=True, methods=["get"], url_path="convert")
    def convert(self, request, pk=None):
        """Convert `?amount=` from this currency into `?target=`."""
        source = self.get_object()
        target_code = request.query_params.get("target")
        amount_raw = request.query_params.get("amount")
        if not target_code or amount_raw is None:
            raise ValidationError(
                {"detail": "Both 'target' and 'amount' query parameters are required."}
            )
        target = Currency.objects.filter(code=target_code.upper(), is_active=True).first()
        if target is None:
            raise ValidationError({"target": f"Unknown or inactive currency '{target_code}'."})

        try:
            amount = Decimal(str(amount_raw))
        except Exception as exc:
            raise ValidationError({"amount": "Must be a decimal number."}) from exc

        return Response(
            {
                "source": source.code,
                "target": target.code,
                "amount": amount,
                "rate": Decimal(target.exchange_rate) / Decimal(source.exchange_rate),
                "converted_amount": source.convert_to(amount, target),
            }
        )

    @action(detail=False, methods=["post"], url_path="refresh", permission_classes=[IsAdminUser])
    def refresh(self, request):
        """Re-fetch every rate from the provider (staff only)."""
        from .services import ExchangeRateError, record_failure, refresh_rates

        base_code = request.data.get("base") or None
        try:
            result = refresh_rates(base_code=base_code)
        except ExchangeRateError as exc:
            record_failure("exchangerate-api", base_code or "", str(exc))
            return Response({"detail": str(exc)}, status=502)
        return Response(
            {
                "source": result.source,
                "updated": result.updated,
                "created": result.created,
                "message": result.message,
            }
        )
