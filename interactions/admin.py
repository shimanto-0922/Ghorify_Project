from django.contrib import admin
from .models import Favourite, Comparison, ComparisonItem

admin.site.register(Favourite)
admin.site.register(Comparison)
admin.site.register(ComparisonItem)
