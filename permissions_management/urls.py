# permissions_dashboard/urls.py
from django.urls import path
from .views import PermissionMatrixView, toggle_permission_ajax

app_name = "permissions_dashboard"

urlpatterns = [
    path('', PermissionMatrixView.as_view(), name='permission-matrix'),
    path('toggle-perm/', toggle_permission_ajax, name='toggle-permission'),
]
