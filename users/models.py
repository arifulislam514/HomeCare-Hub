from django.db import models
from django.contrib.auth.models import AbstractUser
from users.managers import CustomUserManager

class User(AbstractUser):
    username = None
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField(unique=True)
    address = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    # role field
    CLIENT = 'Client'
    ADMIN = 'Admin'
    ROLE_CHOICES = [
        (CLIENT, 'Client'),
        (ADMIN, 'Admin'),
    ]
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=CLIENT
    )
    
    USERNAME_FIELD = 'email'  # Use email instead of username
    # No additional fields are required for superuser creation; only email and password are needed.
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email if self.email else f"User(id={self.id})"

