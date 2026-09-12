from rest_framework import serializers

from apps.accounts.models import Account
from apps.accounts.serializers import AccountSerializer
from apps.budgets.models import Budget
from apps.currencies.models import Currency
from apps.currencies.serializers import CurrencySerializer

from .models import Category, Transaction
from .services import TransactionRuleError, validate_transaction_payload


class CategorySerializer(serializers.ModelSerializer):
    budget = serializers.PrimaryKeyRelatedField(
        queryset=Budget.objects.none(), required=False, allow_null=True
    )
    transaction_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Category
        fields = ["id", "name", "budget", "is_active", "transaction_count"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            # Scoping the queryset is what stops a user from attaching their
            # category to somebody else's budget.
            self.fields["budget"].queryset = Budget.objects.filter(user=request.user)

    def validate_name(self, value: str) -> str:
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            qs = Category.objects.filter(user=request.user, name__iexact=value.strip())
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("You already have a category with this name.")
        return value.strip()


class TransactionSerializer(serializers.ModelSerializer):
    """Reads are denormalised for the UI; writes accept primary keys only.

    Related-field querysets are scoped to the requesting user, and the shared
    service layer re-checks ownership so a crafted request cannot reference
    another tenant's account, category or budget.
    """

    account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.none())
    destination_account = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.none(), required=False, allow_null=True
    )
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.none(), required=False, allow_null=True
    )
    budget = serializers.PrimaryKeyRelatedField(
        queryset=Budget.objects.none(), required=False, allow_null=True
    )
    currency = serializers.PrimaryKeyRelatedField(
        queryset=Currency.objects.filter(is_active=True), required=False
    )

    account_detail = AccountSerializer(source="account", read_only=True)
    destination_account_detail = AccountSerializer(source="destination_account", read_only=True)
    category_detail = CategorySerializer(source="category", read_only=True)
    budget_detail = serializers.SerializerMethodField()
    currency_detail = CurrencySerializer(source="currency", read_only=True)
    transaction_type_display = serializers.CharField(
        source="get_transaction_type_display", read_only=True
    )
    signed_amount = serializers.DecimalField(
        max_digits=20, decimal_places=2, read_only=True
    )

    class Meta:
        model = Transaction
        fields = [
            "id",
            "account",
            "account_detail",
            "destination_account",
            "destination_account_detail",
            "transaction_type",
            "transaction_type_display",
            "transaction_date",
            "amount",
            "signed_amount",
            "currency",
            "currency_detail",
            "exchange_rate",
            "description",
            "category",
            "category_detail",
            "budget",
            "budget_detail",
            "created_date",
            "updated_date",
        ]
        read_only_fields = ["created_date", "updated_date"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            owned_accounts = Account.objects.filter(user=request.user, is_active=True)
            self.fields["account"].queryset = owned_accounts
            self.fields["destination_account"].queryset = owned_accounts
            self.fields["category"].queryset = Category.objects.filter(user=request.user)
            self.fields["budget"].queryset = Budget.objects.filter(user=request.user)

    def get_budget_detail(self, obj):
        if obj.budget_id is None:
            return None
        return {"id": obj.budget_id, "name": obj.budget.name, "currency": obj.budget.currency_id}

    def validate(self, attrs):
        # Delegate the cross-field rules to the single source of truth so the API
        # and the admin behave identically.
        merged = {}
        for field in (
            "account",
            "destination_account",
            "category",
            "budget",
            "currency",
            "transaction_type",
            "transaction_date",
            "amount",
            "exchange_rate",
            "description",
        ):
            if field in attrs:
                merged[field] = attrs[field]
            elif self.instance is not None:
                merged[field] = getattr(self.instance, field)
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            raise serializers.ValidationError({"detail": "Authentication is required."})
        try:
            cleaned = validate_transaction_payload(request.user, merged, instance=self.instance)
        except TransactionRuleError as exc:
            raise serializers.ValidationError(
                getattr(exc, "message_dict", None) or {"detail": exc.messages}
            )
        # Keep the currency the service layer resolved (it defaults to the
        # account currency) so `validated_data` is complete for create().
        if cleaned.get("currency") is not None and "currency" not in attrs:
            attrs["currency"] = cleaned["currency"]
        return attrs


class TransactionSummarySerializer(serializers.Serializer):
    """Aggregated income/expense totals for a period, in one currency."""

    period_start = serializers.DateField()
    period_end = serializers.DateField()
    currency = serializers.CharField(allow_null=True)
    total_income = serializers.DecimalField(max_digits=24, decimal_places=2)
    total_expenses = serializers.DecimalField(max_digits=24, decimal_places=2)
    net = serializers.DecimalField(max_digits=24, decimal_places=2)
    transaction_count = serializers.IntegerField()
    by_category = serializers.ListField(child=serializers.DictField(), required=False)
