from rest_framework import serializers

from apps.accounts.models import Account
from apps.currencies.models import Currency
from apps.currencies.serializers import CurrencySerializer

from .models import Holding, Valuation


class ValuationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Valuation
        fields = ["id", "holding", "valued_on", "value", "note", "created_date"]
        read_only_fields = ["created_date"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            self.fields["holding"].queryset = Holding.objects.filter(user=request.user)


class HoldingSerializer(serializers.ModelSerializer):
    account = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.none(), required=False, allow_null=True
    )
    currency = serializers.PrimaryKeyRelatedField(
        queryset=Currency.objects.filter(is_active=True)
    )
    currency_detail = CurrencySerializer(source="currency", read_only=True)
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    market_value = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    unrealised_gain = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    unrealised_gain_percent = serializers.DecimalField(
        max_digits=20, decimal_places=2, read_only=True
    )
    latest_valuation_date = serializers.SerializerMethodField()

    class Meta:
        model = Holding
        fields = [
            "id",
            "symbol",
            "name",
            "kind",
            "kind_display",
            "quantity",
            "cost_basis",
            "currency",
            "currency_detail",
            "account",
            "opened_date",
            "notes",
            "market_value",
            "unrealised_gain",
            "unrealised_gain_percent",
            "latest_valuation_date",
            "created_date",
            "updated_date",
        ]
        read_only_fields = ["created_date", "updated_date"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            self.fields["account"].queryset = Account.objects.filter(user=request.user)

    def get_latest_valuation_date(self, obj):
        valuation = obj.latest_valuation
        return valuation.valued_on if valuation else None

    def validate_symbol(self, value: str) -> str:
        return value.upper().strip()
