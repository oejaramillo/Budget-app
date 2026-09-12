from django.contrib import admin

from .models import Currency, ExchangeRateHistory, ExchangeRateSnapshot


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "exchange_rate", "principal", "is_active", "rate_updated_at")
    list_filter = ("is_active", "principal")
    search_fields = ("code", "name")
    ordering = ("code",)


@admin.register(ExchangeRateSnapshot)
class ExchangeRateSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "fetched_at",
        "base_code",
        "source",
        "updated_count",
        "created_count",
        "succeeded",
    )
    list_filter = ("succeeded", "base_code")
    readonly_fields = ("fetched_at",)


@admin.register(ExchangeRateHistory)
class ExchangeRateHistoryAdmin(admin.ModelAdmin):
    list_display = ("currency", "rate", "snapshot")
    list_filter = ("currency__code",)
