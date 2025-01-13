from django.urls import path
from .views import *

app_name = 'inv'

urlpatterns = [
    path('assets/', AssetListView.as_view(), name='asset_list'),
    path('activos/<str:abbreviation>/equipos/', ActivoEquipmentListView.as_view(), name='asset_equipment_list'),

    path('public/equipo/<str:eq_code>/', public_equipo_detail, name='public_equipo_detail'),
    path('activos/<str:abbreviation>/export_excel/', export_equipment_supplies, name='export_equipment_supplies'),
    path('activos/<str:abbreviation>/create_supply/', create_supply_view, name='create_supply'),

    path('all/equipos/', AllAssetsEquipmentListView.as_view(), name='all_equipment_list'),
    path('equipo/<str:equipo_code>/dar_baja/', DarBajaCreateView.as_view(), name='dar_baja'),

]
