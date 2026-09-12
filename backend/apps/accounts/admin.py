from django.contrib import admin

from .models import Account


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "account_type", "balance", "currency", "is_active")
    list_filter = ("account_type", "is_active", "currency")
    search_fields = ("name", "institution", "official_number", "user__username")
    autocomplete_fields = ("user",)
    list_select_related = ("user", "currency")
