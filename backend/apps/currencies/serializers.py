from django.utils import timezone
from rest_framework import serializers

from .models import Currency


class CurrencySerializer(serializers.ModelSerializer):
    rate_age_hours = serializers.SerializerMethodField()

    class Meta:
        model = Currency
        fields = [
            "id",
            "code",
            "name",
            "symbol",
            "exchange_rate",
            "principal",
            "is_active",
            "rate_updated_at",
            "rate_age_hours",
        ]
        read_only_fields = ["rate_updated_at"]

    def validate_code(self, value: str) -> str:
        code = Currency.normalise_code(value)
        if len(code) != 3 or not code.isalpha():
            raise serializers.ValidationError(
                "Use a 3-letter ISO 4217 code, for example 'EUR'."
            )
        qs = Currency.objects.filter(code=code)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This currency already exists.")
        return code

    def get_rate_age_hours(self, obj) -> float | None:
        if not obj.rate_updated_at:
            return None
        return round((timezone.now() - obj.rate_updated_at).total_seconds() / 3600, 2)

    def validate_principal(self, value: bool) -> bool:
        if value:
            existing = Currency.objects.filter(principal=True)
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError(
                    "Only one currency can be the principal reporting currency."
                )
        return value


class CurrencySummarySerializer(serializers.Serializer):
    """Read-only aggregation of a user's balances expressed in one currency."""

    currency_code = serializers.CharField()
    currency_name = serializers.CharField()
    total_balance = serializers.DecimalField(max_digits=24, decimal_places=2)
    account_count = serializers.IntegerField()
    converted = serializers.BooleanField()
    conversion_rate = serializers.DecimalField(
        max_digits=24, decimal_places=12, allow_null=True
    )
