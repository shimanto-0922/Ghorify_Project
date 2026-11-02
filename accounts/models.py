from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    # One account can look for a home and also post a property.
    # Only the platform admin has a different role.
    ROLE_CHOICES = [
        ('user', 'User'),
        ('admin', 'Admin'),
    ]

    email = models.EmailField(unique=True, null=True, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    phone = models.CharField(max_length=14, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True, max_length=500)

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_platform_admin(self):
        return self.role == 'admin' or self.is_superuser


class Profile(models.Model):
    STATUS_CHOICES = [
        ('unsubmitted', 'Documents not submitted'),
        ('pending', 'Waiting for review'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    nid_document = models.FileField(upload_to='verification/', blank=True, null=True)
    birth_certificate = models.FileField(upload_to='verification/', blank=True, null=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='unsubmitted')
    review_note = models.CharField(max_length=255, blank=True)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_profiles'
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Profile of {self.user}'
