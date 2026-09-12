from django.contrib import admin

from .models import Budget


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "currency", "max_amount", "start_date", "end_date", "is_active")
    list_filter = ("is_active", "currency")
    search_fields = ("name", "user__username")
    filter_horizontal = ("accounts",)
    list_select_related = ("user", "currency")
