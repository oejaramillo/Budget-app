from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count
from rest_framework import serializers

from .models import OperationRun, OpsSettings


class OperationRunSerializer(serializers.ModelSerializer):
    """A recorded console action."""

    triggered_by_username = serializers.CharField(
        source="triggered_by.username", read_only=True, default=None
    )

    class Meta:
        model = OperationRun
        fields = [
            "id",
            "operation",
            "arguments",
            "status",
            "triggered_by",
            "triggered_by_username",
            "output",
            "error",
            "result",
            "duration_ms",
            "started_at",
            "finished_at",
        ]
        read_only_fields = fields


class OperationRequestSerializer(serializers.Serializer):
    """Body of `POST /api/v1/ops/operations/{key}/run/`."""

    arguments = serializers.DictField(required=False, default=dict)


class OperationSpecSerializer(serializers.Serializer):
    """Read-only description of a registered operation (drives the UI form)."""

    key = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField()
    safety = serializers.CharField()
    group = serializers.CharField()
    fields = serializers.ListField(child=serializers.DictField())
    allowed = serializers.BooleanField()
    blocked_reason = serializers.CharField(allow_blank=True)


class OpsSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OpsSettings
        fields = [
            "allow_mutating_operations",
            "allow_destructive_operations",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]


class TenantSerializer(serializers.ModelSerializer):
    """A tenant account plus its footprint, for the user administration table."""

    account_count = serializers.IntegerField(read_only=True, default=0)
    transaction_count = serializers.IntegerField(read_only=True, default=0)
    holding_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
            "account_count",
            "transaction_count",
            "holding_count",
        ]
        read_only_fields = [
            "id",
            "username",
            "date_joined",
            "last_login",
            "account_count",
            "transaction_count",
            "holding_count",
        ]


class TenantUpdateSerializer(serializers.Serializer):
    """Flags a superuser may change on a tenant.

    Only these three fields are accepted: promoting someone to staff or disabling
    an account is administrative, whereas renaming a user or editing their profile
    is the user's own business through `/auth/me/`.
    """

    is_active = serializers.BooleanField(required=False)
    is_staff = serializers.BooleanField(required=False)
    is_superuser = serializers.BooleanField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                {"detail": "Provide at least one of is_active, is_staff, is_superuser."}
            )
        return attrs


class TenantPasswordSerializer(serializers.Serializer):
    """Administrative password reset."""

    new_password = serializers.CharField(write_only=True, style={"input_type": "password"})

    def validate_new_password(self, value: str) -> str:
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value


class TenantDeleteSerializer(serializers.Serializer):
    """Deleting a tenant requires typing the username back."""

    confirm_username = serializers.CharField()

    def validate_confirm_username(self, value: str) -> str:
        if value != self.context["username"]:
            raise serializers.ValidationError(
                "The confirmation text does not match the username."
            )
        return value


def tenant_queryset():
    """Users annotated with their data footprint (single query, no N+1)."""
    return User.objects.annotate(
        account_count=Count("accounts", distinct=True),
        transaction_count=Count("transactions", distinct=True),
        holding_count=Count("holdings", distinct=True),
    ).order_by("username")
