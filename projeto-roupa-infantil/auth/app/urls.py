from django.urls import path
from . import views

urlpatterns = [
    # Auth endpoints
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
    path('register', views.register, name='register'),
    path('refresh', views.refresh_token, name='refresh_token'),
    path('forgot-password', views.forgot_password, name='forgot_password'),
    path('reset-password', views.reset_password, name='reset_password'),
    path('verify-mfa', views.verify_mfa, name='verify_mfa'),
    
    # User endpoints
    path('profile', views.profile, name='profile'),
    path('profile/update', views.update_profile, name='update_profile'),
    path('change-password', views.change_password, name='change_password'),
    
    # Admin endpoints
    path('users', views.list_users, name='list_users'),
    path('users/<str:user_id>', views.user_detail, name='user_detail'),
]