from rest_framework import viewsets, status
from rest_framework import permissions as drf_permissions
from users.permissions import IsAdminOrSelf
from rest_framework.decorators import action
from rest_framework.response import Response
from users.models import User
from users.serializers import UserSerializer, ChangeRoleSerializer
from users.permissions import IsAdminOrSelf

class UserViewSet(viewsets.ModelViewSet):
    """
    Standard CRUD for users.
    - Non-admins can only see/update their own user.
    - Admins can list and manage all users.
    - `POST /api/v1/users/` should not be used for signup; use Djoser `auth/users/` instead.
    """
    queryset = User.objects.all()
    def get_serializer_class(self):
        if self.action == "change_role":
            return ChangeRoleSerializer
        return UserSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'update', 'partial_update', 'destroy']:
            return [drf_permissions.IsAuthenticated(), IsAdminOrSelf()]
        if self.action in ['me']:
            return [drf_permissions.IsAuthenticated()]
        if self.action in ['change_role']:
            return [drf_permissions.IsAdminUser()]
        # default
        return [drf_permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "Admin"):
            return User.objects.all()
        # Non-admins: only themselves
        return User.objects.filter(id=user.id)
    
    @action(detail=False, methods=['get', 'patch', 'put'])
    def me(self, request):
        """
        Get or update the authenticated user's profile.
        GET /api/v1/users/me/
        PATCH /api/v1/users/me/ {first_name, last_name, address, phone_number}
        """
        user = request.user
        if request.method.lower() == 'get':
            return Response(UserSerializer(user).data)
        serializer = UserSerializer(user, data=request.data, partial=(request.method.lower()=='patch'))
        serializer.is_valid(raise_exception=True)
        # Prevent role change by non-admins
        if 'role' in serializer.validated_data and not (request.user.is_staff or getattr(request.user, "role", None) == "Admin"):
            serializer.validated_data.pop('role')
        serializer.save()
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'], url_path="change_role")
    def change_role(self, request, pk=None):
        """Admins can change a user's role (Client/Admin)."""
        user = self.get_object()
        serializer = ChangeRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_role = serializer.validated_data['role']
        user.role = new_role
        user.is_staff = True if new_role == User.ADMIN else False
        user.save()
        return Response(
            {
                "status": f"{user.email}'s role updated successfully",
                "new_role": user.role
            },
            status=status.HTTP_200_OK
        )
