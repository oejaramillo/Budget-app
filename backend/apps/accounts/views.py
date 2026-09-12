from decimal import Decimal, InvalidOperation

from django.db.models import Sum
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.currencies.models import Currency

from .models import Account
from .serializers import AccountBalanceSerializer, AccountSerializer


class AccountViewSet(viewsets.ModelViewSet):
    """CRUD for the authenticated user's accounts.

    The queryset is scoped to `request.user` for every action, so an object that
    belongs to somebody else is indistinguishable from one that does not exist
    (404 rather than 403, which avoids leaking IDs).
    """

    serializer_class = AccountSerializer
    filterset_fields = ["account_type", "currency", "institution", "is_active"]
    search_fields = ["name", "institution", "official_number"]
    ordering_fields = ["balance", "created_date", "last_updated", "name"]

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user).select_related("currency")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["get"], url_path="balances")
    def balances(self, request):
        """Every account balance, optionally converted to `?target=CODE`."""
        target_code = request.query_params.get("target")
        target = None
        if target_code:
            target = Currency.objects.filter(code=target_code.upper()).first()
            if target is None:
                raise ValidationError({"target": f"Unknown currency '{target_code}'."})

        rows = []
        for account in self.get_queryset():
            reference_balance = None
            if target is not None:
                reference_balance = account.currency.convert_to(account.balance, target)
            rows.append(
                {
                    "account_id": account.pk,
                    "account_name": account.name,
                    "currency": account.currency.code,
                    "balance": account.balance,
                    "reference_balance": reference_balance,
                    "reference_currency": target.code if target else None,
                }
            )
        return Response(AccountBalanceSerializer(rows, many=True).data)

    @action(detail=True, methods=["post"], url_path="adjust-balance")
    def adjust_balance(self, request, pk=None):
        """Set the account balance explicitly (opening balance or reconciliation).

        The balance is read-only in the serializer because routine movements must
        come from transactions; this endpoint is the deliberate escape hatch.
        """
        account = self.get_object()
        raw = request.data.get("balance")
        try:
            new_balance = Decimal(str(raw))
        except (InvalidOperation, TypeError):
            raise ValidationError({"balance": "A decimal number is required."})

        account.balance = new_balance.quantize(Decimal("0.01"))
        account.save(update_fields=["balance", "last_updated"])
        return Response(AccountSerializer(account, context={"request": request}).data)

    @action(detail=False, methods=["get"], url_path="net-worth")
    def net_worth(self, request):
        """Total of all balances per currency, plus the converted total if asked."""
        target_code = request.query_params.get("target")
        target = None
        if target_code:
            target = Currency.objects.filter(code=target_code.upper()).first()
            if target is None:
                raise ValidationError({"target": f"Unknown currency '{target_code}'."})

        per_currency = list(
            self.get_queryset()
            .values("currency__code")
            .annotate(total=Sum("balance"))
            .order_by("currency__code")
        )

        converted_total = Decimal("0.00")
        for row in per_currency:
            amount = row["total"] or Decimal("0.00")
            if target is None:
                continue
            currency = Currency.objects.filter(code=row["currency__code"]).first()
            if currency is not None:
                converted_total += currency.convert_to(amount, target)

        return Response(
            {
                "per_currency": [
                    {
                        "currency": row["currency__code"],
                        "total": row["total"] or Decimal("0.00"),
                    }
                    for row in per_currency
                ],
                "target_currency": target.code if target else None,
                "converted_total": converted_total if target else None,
            }
        )
