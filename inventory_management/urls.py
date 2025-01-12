from django.urls import path
from .views import *

app_name = 'inv'

urlpatterns = [
    path('assets/', AssetListView.as_view(), name='asset_list'),
    path('activos/<str:abbreviation>/equipos/', ActivoEquipmentListView.as_view(), name='asset_equipment_list'),
]
