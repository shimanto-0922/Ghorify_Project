from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),

    # Platform admin pages
    path('admin/', views.admin_overview, name='admin_overview'),
    path('admin/listings/', views.moderation_list, name='moderation_list'),
    path('admin/listings/<int:property_id>/moderate/', views.moderate_property, name='moderate_property'),
    path('admin/verification/', views.verification_list, name='verification_list'),
    path('admin/verification/<int:profile_id>/verify/', views.verify_user, name='verify_user'),
    path('admin/users/', views.user_list, name='user_list'),
    path('admin/users/<int:user_id>/toggle/', views.toggle_user, name='toggle_user'),
]
