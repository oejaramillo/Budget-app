from django.contrib import admin

from .models import Category, Transaction


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "budget", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "user__username")
    list_select_related = ("user", "budget")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_date",
        "user",
        "transaction_type",
        "amount",
        "currency",
        "account",
        "category",
    )
    list_filter = ("transaction_type", "transaction_date", "currency")
    search_fields = ("description", "account__name", "user__username")
    date_hierarchy = "transaction_date"
    list_select_related = ("user", "account", "currency", "category")
    autocomplete_fields = ("category",)
