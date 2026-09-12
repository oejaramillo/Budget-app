from django.contrib import admin

from .models import Holding, Valuation


class ValuationInline(admin.TabularInline):
    model = Valuation
    extra = 0


@admin.register(Holding)
class HoldingAdmin(admin.ModelAdmin):
    list_display = ("symbol", "user", "kind", "quantity", "cost_basis", "currency")
    list_filter = ("kind", "currency")
    search_fields = ("symbol", "name", "user__username")
    list_select_related = ("user", "currency", "account")
    inlines = [ValuationInline]


@admin.register(Valuation)
class ValuationAdmin(admin.ModelAdmin):
    list_display = ("holding", "valued_on", "value")
    list_filter = ("valued_on",)
    search_fields = ("holding__symbol",)
