"""Superuser console endpoints.

Everything under `/api/v1/ops/` is gated on `IsSuperUser`. The console can run
service-wide maintenance and read every tenant's footprint, so `is_staff` alone is
not enough.
"""

from django.contrib.auth.models import User
from django.db.models import Count, Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import OperationRun, OpsSettings
from .permissions import IsSuperUser
from .serializers import (
    OperationRequestSerializer,
    OperationRunSerializer,
    OperationSpecSerializer,
    OpsSettingsSerializer,
    TenantDeleteSerializer,
    TenantPasswordSerializer,
    TenantSerializer,
    TenantUpdateSerializer,
    tenant_queryset,
)
from .services import (
    OperationError,
    app_inventory,
    check_data_integrity,
    clean_arguments,
    collect_system_stats,
    execute_operation,
    get_operation,
    rate_freshness,
    registry_payload,
)


class SystemOverviewView(APIView):
    """The console's landing data: counts, database, rate freshness, registry."""

    permission_classes = [IsSuperUser]

    def get(self, request):
        return Response(
            {
                "stats": collect_system_stats(),
                "integrity": check_data_integrity(),
                "rates": rate_freshness(),
                "operations": registry_payload(),
                "apps": app_inventory(),
                "settings": OpsSettingsSerializer(OpsSettings.load()).data,
            }
        )


class OperationViewSet(viewsets.ViewSet):
    """List maintenance operations, run them, and browse the audit trail."""

    permission_classes = [IsSuperUser]
    lookup_field = "key"

    def list(self, request):
        return Response(OperationSpecSerializer(registry_payload(), many=True).data)

    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request):
        """Recent runs, newest first, optionally filtered."""
        queryset = OperationRun.objects.select_related("triggered_by")

        operation_key = request.query_params.get("operation")
        if operation_key:
            queryset = queryset.filter(operation=operation_key)
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return Response(OperationRunSerializer(queryset[:100], many=True).data)

    @action(detail=True, methods=["post"], url_path="run")
    def run(self, request, key=None):
        """Execute one operation and return its recorded run."""
        spec = get_operation(key)
        if spec is None:
            return Response(
                {"detail": f"Unknown operation '{key}'."}, status=status.HTTP_404_NOT_FOUND
            )

        request_serializer = OperationRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        try:
            arguments = clean_arguments(spec, request_serializer.validated_data["arguments"])
        except OperationError as exc:
            raise ValidationError({"arguments": str(exc)}) from exc

        try:
            run = execute_operation(spec, arguments, user=request.user)
        except OperationError as exc:
            # Policy refusal rather than a crash: report it as a conflict.
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        http_status = (
            status.HTTP_502_BAD_GATEWAY
            if run.status == OperationRun.Status.FAILED
            else status.HTTP_200_OK
        )
        return Response(OperationRunSerializer(run).data, status=http_status)


class OpsSettingsView(APIView):
    """Read and update the console's safety switches."""

    permission_classes = [IsSuperUser]

    def get(self, request):
        return Response(OpsSettingsSerializer(OpsSettings.load()).data)

    def patch(self, request):
        instance = OpsSettings.load()
        serializer = OpsSettingsSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class TenantViewSet(viewsets.ModelViewSet):
    """Tenant (user) administration.

    Deliberately narrow: account flags, password reset and deletion. Profile data
    belongs to the user and is edited through `/auth/me/`.
    """

    permission_classes = [IsSuperUser]
    serializer_class = TenantSerializer
    filterset_fields = ["is_active", "is_staff", "is_superuser"]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering_fields = ["username", "date_joined", "last_login"]
    http_method_names = ["get", "patch", "delete", "post", "head", "options"]

    def get_queryset(self):
        return tenant_queryset()

    def _guard_self(self, request, target: User, data: dict) -> None:
        """Stop an operator from locking themselves out."""
        if target.pk != request.user.pk:
            return
        if data.get("is_active") is False:
            raise ValidationError({"is_active": "You cannot deactivate your own account."})
        if data.get("is_staff") is False:
            raise ValidationError({"is_staff": "You cannot remove your own staff access."})
        if data.get("is_superuser") is False:
            raise ValidationError(
                {"is_superuser": "You cannot remove your own superuser access."}
            )

    def _guard_last_superuser(self, target: User, data: dict) -> None:
        """Never allow the last active superuser to be demoted, disabled or deleted."""
        losing_superuser = target.is_superuser and (
            data.get("is_superuser") is False or data.get("is_active") is False
        )
        if not losing_superuser:
            return
        remaining = (
            User.objects.filter(is_superuser=True, is_active=True).exclude(pk=target.pk).exists()
        )
        if not remaining:
            raise ValidationError(
                {
                    "detail": (
                        "This is the only active superuser. Create or promote another "
                        "account before changing this one."
                    )
                }
            )

    def partial_update(self, request, *args, **kwargs):
        target = self.get_object()
        serializer = TenantUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        self._guard_self(request, target, data)
        self._guard_last_superuser(target, data)

        for field, value in data.items():
            setattr(target, field, value)
        target.save(update_fields=list(data.keys()))

        return Response(TenantSerializer(self.get_queryset().get(pk=target.pk)).data)

    @action(detail=True, methods=["post"], url_path="set-password")
    def set_password(self, request, pk=None):
        """Reset a tenant's password through Django's validators.

        Note that this does not revoke tokens already issued to that tenant; they
        expire on their own schedule. Deactivate the account to cut access now.
        """
        target = self.get_object()
        serializer = TenantPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target.set_password(serializer.validated_data["new_password"])
        target.save(update_fields=["password"])
        return Response({"detail": f"Password updated for '{target.username}'."})

    def destroy(self, request, *args, **kwargs):
        """Delete a tenant and every row they own, after typed confirmation."""
        target = self.get_object()
        if target.pk == request.user.pk:
            raise ValidationError({"detail": "You cannot delete your own account."})
        self._guard_last_superuser(target, {"is_active": False})

        serializer = TenantDeleteSerializer(
            data=request.data, context={"username": target.username}
        )
        serializer.is_valid(raise_exception=True)

        username = target.username
        counts = {
            "accounts": target.accounts.count(),
            "transactions": target.transactions.count(),
            "budgets": target.budgets.count(),
            "categories": target.categories.count(),
            "holdings": target.holdings.count(),
        }
        target.delete()
        return Response(
            {"detail": f"Deleted '{username}' and all owned data.", "deleted": counts}
        )

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """Headline numbers for the administration screen."""
        return Response(
            User.objects.aggregate(
                total=Count("id"),
                active=Count("id", filter=Q(is_active=True)),
                staff=Count("id", filter=Q(is_staff=True)),
                superusers=Count("id", filter=Q(is_superuser=True)),
            )
        )
