# ============================================================
# permissions.py
# ============================================================
# WHY: DRF's built-in IsAuthenticated only checks that a valid JWT
# token is present. It does NOT check whether the object being accessed
# belongs to the authenticated user. Without a custom permission,
# a logged-in user could hit /api/portfolio/2/ and read another
# user's data if they guessed the ID.
#
# HOW DRF calls this:
#   1. View calls check_object_permissions(request, obj)
#   2. DRF iterates over permission_classes
#   3. For each permission, calls has_object_permission(request, view, obj)
#   4. If any returns False → 403 Forbidden
#
# We use this on detail views (RetrieveUpdateDestroyAPIView) where
# a specific object is fetched by PK. For list views, ownership is
# enforced by get_queryset() scoping instead.
# ============================================================

from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """
    Object-level permission: only allows access if the object
    is owned by the authenticated user.

    Works for both Portfolio (obj.user) and Project (obj.portfolio.user).
    """
    message = "You do not have permission to access this resource."

    def has_object_permission(self, request, view, obj):
        # Portfolio has a direct .user field.
        if hasattr(obj, "user"):
            return obj.user == request.user

        # Project is linked via portfolio → user.
        if hasattr(obj, "portfolio"):
            return obj.portfolio.user == request.user

        return False
