"""
Project-level URL configuration for pothole_system.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('pothole_api.urls')),
    path('dashboard/', include('pothole_api.dashboard_urls')),
    path('', include('pothole_api.dashboard_urls')),  # redirect root to dashboard
]
