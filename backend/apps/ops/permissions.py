"""Permissions for the superuser console.

The console exposes destructive, service-wide actions, so it is gated on
`is_superuser` rather than DRF's `IsAdminUser` (which only checks `is_staff`).
"""

from rest_framework.permissions import BasePermission


class IsSuperUser(BasePermission):
    """Allow access only to active superusers.

    Staff-but-not-superuser accounts are rejected on purpose: `is_staff` grants
    access to the Django admin, which is a different (and narrower) trust level
    than "may run maintenance commands against every tenant's data".
    """

    message = "This area is restricted to superusers."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.is_active and user.is_superuser)
