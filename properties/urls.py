from django.urls import path
from . import views

app_name = 'properties'

urlpatterns = [
    # Home page and listings
    path('', views.home, name='home'),
    path('properties/', views.property_list, name='property_list'),
    path('properties/<int:property_id>/', views.property_detail, name='property_detail'),

    # Property CRUD
    path('my-properties/', views.my_properties, name='my_properties'),
    path('my-properties/create/', views.property_create, name='property_create'),
    path('my-properties/<int:property_id>/edit/', views.property_update, name='property_update'),
    path('my-properties/<int:property_id>/delete/', views.property_delete, name='property_delete'),

    # Photo CRUD
    path('my-properties/<int:property_id>/photos/', views.image_list, name='image_list'),
    path('my-properties/<int:property_id>/photos/<int:image_id>/edit/', views.image_update, name='image_update'),
    path('my-properties/<int:property_id>/photos/<int:image_id>/delete/', views.image_delete, name='image_delete'),
    path('my-properties/<int:property_id>/photos/<int:image_id>/cover/', views.image_make_primary, name='image_make_primary'),

    # Utility CRUD
    path('my-properties/<int:property_id>/utilities/', views.utility_list, name='utility_list'),
    path('my-properties/<int:property_id>/utilities/<int:utility_id>/edit/', views.utility_update, name='utility_update'),
    path('my-properties/<int:property_id>/utilities/<int:utility_id>/delete/', views.utility_delete, name='utility_delete'),
]
