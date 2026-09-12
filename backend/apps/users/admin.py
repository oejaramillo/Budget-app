from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User


class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_active", "is_superuser")
    search_fields = ("username", "email")


# Re-register the default User with a slightly friendlier admin.
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.site_header = "Budget App administration"
admin.site.site_title = "Budget App"
admin.site.index_title = "Operations"
