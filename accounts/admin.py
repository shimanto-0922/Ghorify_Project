from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Profile

# UserAdmin keeps the password fields working in the Django admin
admin.site.register(User, UserAdmin)
admin.site.register(Profile)
