from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from core import views

def health_check(request):
    return JsonResponse({'status': 'healthy', 'service': 'api-gateway'})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health_check'),
    
    # Auth routes - proxy para auth-service
    path('api/auth/login', views.proxy_to_auth, name='login'),
    path('api/auth/logout', views.proxy_to_auth, name='logout'),
    path('api/auth/register', views.proxy_to_auth, name='register'),
    path('api/auth/refresh', views.proxy_to_auth, name='refresh'),
    path('api/auth/forgot-password', views.proxy_to_auth, name='forgot_password'),
    path('api/auth/reset-password', views.proxy_to_auth, name='reset_password'),
    path('api/auth/verify-mfa', views.proxy_to_auth, name='verify_mfa'),
    
    # User routes - proxy para auth-service
    path('api/users/', views.proxy_to_auth, name='users'),
    path('api/users/profile', views.proxy_to_auth, name='profile'),
    path('api/users/change-password', views.proxy_to_auth, name='change_password'),
    
    # Task routes - proxy para task-service
    path('api/tasks/', views.proxy_to_tasks, name='tasks'),
    path('api/tasks/<str:task_id>', views.proxy_to_tasks, name='task_detail'),
    
    # Reports routes - proxy para task-service
    path('api/reports/', views.proxy_to_tasks, name='reports'),
    
    # Notifications routes - proxy para task-service
    path('api/notifications/', views.proxy_to_tasks, name='notifications'),
    
    # File upload - proxy para task-service
    path('api/files/', views.proxy_to_tasks, name='files'),
    
    # Admin routes - requer validação especial
    path('api/admin/', views.admin_proxy, name='admin'),
    
    # Metrics
    path('api/metrics/', include('django_prometheus.urls')),
]