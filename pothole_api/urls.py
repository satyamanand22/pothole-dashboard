"""
URL patterns for the pothole REST API.
"""

from django.urls import path
from .views import PotholeDataView, DashboardView, DiagnosticView

urlpatterns = [
    path('pothole-data/', PotholeDataView.as_view(), name='pothole-data'),
    path('debug/', DiagnosticView.as_view(), name='pothole-debug'),
]
