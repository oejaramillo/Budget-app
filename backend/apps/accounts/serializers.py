from rest_framework import serializers

from apps.currencies.models import Currency
from apps.currencies.serializers import CurrencySerializer

from .models import Account


class AccountSerializer(serializers.ModelSerializer):
    currency_detail = CurrencySerializer(source="currency", read_only=True)
    account_type_display = serializers.CharField(
        source="get_account_type_display", read_only=True
    )

    class Meta:
        model = Account
        fields = [
            "id",
            "name",
            "account_type",
            "account_type_display",
            "balance",
            "currency",
            "currency_detail",
            "institution",
            "official_number",
            "is_active",
            "created_date",
            "last_updated",
        ]
        read_only_fields = ["created_date", "last_updated", "balance"]

    def validate_currency(self, value: Currency) -> Currency:
        if not value.is_active:
            raise serializers.ValidationError(
                f"Currency {value.code} is inactive and cannot be used for new accounts."
            )
        return value

    def validate_name(self, value: str) -> str:
        """Enforce the per-user unique name at the API layer.

        The database constraint is the safety net; catching it here turns a 500
        into a readable 400.
        """
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            qs = Account.objects.filter(user=request.user, name__iexact=value.strip())
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("You already have an account with this name.")
        return value.strip()


class AccountBalanceSerializer(serializers.Serializer):
    account_id = serializers.IntegerField()
    account_name = serializers.CharField()
    currency = serializers.CharField()
    balance = serializers.DecimalField(max_digits=24, decimal_places=2)
    reference_balance = serializers.DecimalField(
        max_digits=24, decimal_places=2, allow_null=True
    )
    reference_currency = serializers.CharField(allow_null=True)
