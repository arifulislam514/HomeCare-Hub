from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer, UserSerializer as BaseUserSerializer
from rest_framework import serializers
from users.models import User

class UserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = ['id', 'email', 'password', 'first_name',
                  'last_name', 'address', 'phone_number']
        extra_kwargs = {'password': {'write_only': True}}


class UserSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer.Meta):
        model = User
        ref_name = 'CustomUser'
        fields = ['id', 'email', 'first_name',
                  'last_name', 'address', 'phone_number', 'role', 'bio',
                  'avatar', 'facebook', 'twitter', 'linkedin']
        read_only_fields = ['id', 'email', 'role']  # normal users cannot set role
        

class ChangeRoleSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=[User.ADMIN, User.CLIENT])

    class Meta:
        fields = ['role']