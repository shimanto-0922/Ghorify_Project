from django.urls import path
from . import views

app_name = 'interactions'

urlpatterns = [
    # Favourites
    path('favourites/', views.favourite_list, name='favourite_list'),
    path('favourites/<int:property_id>/toggle/', views.favourite_toggle, name='favourite_toggle'),

    # Compare
    path('compare/', views.compare_select, name='compare_select'),
    path('compare/<int:comparison_id>/', views.comparison_detail, name='comparison_detail'),
]
