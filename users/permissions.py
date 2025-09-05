from rest_framework import permissions

class IsAdminOrSelf(permissions.BasePermission):
    """
    Allow access if the user is admin, or the object is the requesting user.
    """
    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_authenticated:
            if request.user.is_staff or getattr(request.user, "role", None) == "Admin":
                return True
            return obj == request.user
        return False
