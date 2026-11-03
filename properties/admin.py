from django.contrib import admin
from .models import Amenity, Property, PropertyImage, Utility

admin.site.register(Amenity)
admin.site.register(Property)
admin.site.register(PropertyImage)
admin.site.register(Utility)
