from django.urls import path
from .views import *

app_name = 'inv'

urlpatterns = [
    path('system/<int:pk>/new_equipo/', EquipoCreateView.as_view(), name='equipo-create'),
    path('equipo/<str:pk>/update/', EquipoUpdate.as_view(), name='equipo-update'),

    path('activos/<str:abbreviation>/equipos/', ActivoEquipmentListView.as_view(), name='asset_equipment_list'),

    path('public/equipo/<str:eq_code>/', public_equipo_detail, name='public_equipo_detail'),


    path('activos/<str:abbreviation>/export_excel/', export_equipment_supplies, name='export_equipment_supplies'),

    path('activos/<str:abbreviation>/create_supply/', create_supply_view, name='create_supply'),

    path('all/equipos/', AllAssetsEquipmentListView.as_view(), name='all_equipment_list'),
    path('equipo/<str:equipo_code>/dar_baja/', DarBajaCreateView.as_view(), name='dar_baja'),

    # Inventory
    path('asset/<str:abbreviation>/suministros/', AssetSuministrosReportView.as_view(), name='asset-suministros'),
    path('asset/<str:abbreviation>/inventario/', AssetInventarioReportView.as_view(), name='asset_inventario_report'),

    # Inv retirements
    path('supply/<int:pk>/retirements/', RetireSupplyCreateView.as_view(), name='retirement-supply'),

    path('activos/<str:abbreviation>/create_new_item_supply/', create_new_item_supply_view, name='create_new_item_supply'),


    path('transaction/<int:transaction_id>/delete/', delete_transaction, name='delete_transaction'),
    path('asset/<str:abbreviation>/historial/pdf/', export_historial_pdf, name='export_historial_pdf'),
    path('transferir/<str:equipo_id>/', transferir_equipo, name='transferir_equipo'),

    path('items/', ItemManagementView.as_view(), name='item_management'),
    path('items/edit/<int:item_id>/', edit_item, name='edit_item'),

    path('sumi/delete/<int:sumi_id>/', delete_sumi, name='delete_sumi'),

    path('transfer/<int:pk>/pdf/', TransferPDFView.as_view(), name='transfer-pdf'),

]
