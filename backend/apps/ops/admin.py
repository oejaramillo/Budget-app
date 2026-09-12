from django.contrib import admin

from .models import OperationRun, OpsSettings


@admin.register(OperationRun)
class OperationRunAdmin(admin.ModelAdmin):
    list_display = (
        "started_at",
        "operation",
        "status",
        "triggered_by",
        "duration_ms",
    )
    list_filter = ("operation", "status")
    search_fields = ("operation", "output", "error", "triggered_by__username")
    date_hierarchy = "started_at"
    list_select_related = ("triggered_by",)
    readonly_fields = (
        "operation",
        "arguments",
        "status",
        "triggered_by",
        "output",
        "error",
        "result",
        "duration_ms",
        "started_at",
        "finished_at",
    )

    def has_add_permission(self, request) -> bool:
        # Runs are created by the dispatcher; hand-adding one would be a lie.
        return False


@admin.register(OpsSettings)
class OpsSettingsAdmin(admin.ModelAdmin):
    list_display = ("allow_mutating_operations", "allow_destructive_operations", "updated_at")

    def has_add_permission(self, request) -> bool:
        return not OpsSettings.objects.exists()

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
