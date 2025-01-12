from django.urls import path
from .views import *

app_name = 'inv'

urlpatterns = [
    path('assets/', AssetListView.as_view(), name='asset_list'),
    path('activos/<str:abbreviation>/equipos/', ActivoEquipmentListView.as_view(), name='asset_equipment_list'),

    path('public/equipo/<str:eq_code>/', public_equipo_detail, name='public_equipo_detail'),
]
