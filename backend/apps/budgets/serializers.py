from django.db.models import Sum
from rest_framework import serializers

from apps.accounts.models import Account
from apps.currencies.models import Currency
from apps.currencies.serializers import CurrencySerializer

from .models import Budget


class BudgetSerializer(serializers.ModelSerializer):
    currency_detail = CurrencySerializer(source="currency", read_only=True)
    accounts = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Account.objects.none(), required=False
    )
    spent_amount = serializers.SerializerMethodField()
    is_current = serializers.BooleanField(read_only=True)

    class Meta:
        model = Budget
        fields = [
            "id",
            "name",
            "min_amount",
            "max_amount",
            "spent_amount",
            "currency",
            "currency_detail",
            "start_date",
            "end_date",
            "accounts",
            "is_active",
            "is_current",
            "created_date",
        ]
        read_only_fields = ["created_date"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            # Owning the queryset here is what prevents linking another user's
            # account to a budget: an unknown ID fails validation cleanly.
            self.fields["accounts"].child_relation.queryset = Account.objects.filter(
                user=request.user
            )

    def validate(self, attrs):
        min_amount = attrs.get("min_amount", getattr(self.instance, "min_amount", None))
        max_amount = attrs.get("max_amount", getattr(self.instance, "max_amount", None))
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))

        if min_amount is not None and max_amount is not None and min_amount > max_amount:
            raise serializers.ValidationError(
                {"min_amount": "Minimum amount cannot be greater than the maximum amount."}
            )
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                {"end_date": "End date must be on or after the start date."}
            )
        return attrs

    def get_spent_amount(self, obj):
        """Sum of expenses linked to this budget.

        Requires the view to have annotated `spent_amount`; falls back to a query
        so the serializer stays correct when used on its own.
        """
        annotated = getattr(obj, "spent_amount", None)
        if annotated is not None:
            return annotated
        from apps.transactions.models import Transaction

        return (
            Transaction.objects.filter(budget=obj, transaction_type="expense").aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )
