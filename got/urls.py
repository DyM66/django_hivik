from django.urls import path
from . import views

app_name = 'got'

urlpatterns = [

    path('mantenimiento/', views.MaintenanceDashboardView.as_view(), name='maintenance_dashboard'),
    path('buceo/', views.buceomtto, name='buceomtto'),
    path("dash/", views.indicadores, name='dashboard'),


    path('profile/', views.profile_update, name='profile_update'),
    path("", views.AssetsListView.as_view(), name="asset-list"),
    path("asset/<str:pk>/", views.AssetDetailView.as_view(), name="asset-detail"),
    path("asset/<str:pk>/maintenance-plan/", views.AssetMaintenancePlanView.as_view(), name="asset-maintenance-plan"),
    path('asset/rutinas/<str:pk>/', views.preventivo_pdf, name='preventivo'),
    path('asset/<str:asset_id>/add-document/', views.AssetDocCreateView.as_view(), name='add-document'),


    path('asset/<str:abbreviation>/suministros/', views.asset_suministros_report, name='asset-suministros'),
    path('asset/<str:abbreviation>/inventario/', views.asset_inventario_report, name='asset_inventario_report'),
    path('transactions/<int:transaction_id>/delete/', views.delete_transaction, name='delete_transaction'),

    path("asset/<str:pk>/schedule/", views.schedule, name="schedule"),
    path('assets/<str:asset_id>/generate-pdf/', views.generate_asset_pdf, name='generate_asset_pdf'),
    path('asset/acta/<str:pk>/', views.acta_entrega_pdf, name='acta_entrega'),

    path("systems/<int:pk>/", views.SysDetailView.as_view(), name="sys-detail"), # VERIFICAR USO
    path('systems/<int:pk>/<str:view_type>/', views.SysDetailView.as_view(), name='sys-detail-view'),
    path('system/<int:pk>/update/', views.SysUpdate.as_view(), name='sys-update'),
    path('system/<int:pk>/delete/', views.SysDelete.as_view(), name='sys-delete'),
    path('systems/<str:asset_id>/<int:system_id>/pdf/', views.system_maintence_pdf, name='generate-system-pdf'),

    path('system/<int:pk>/new_equipo/', views.EquipoCreateView.as_view(), name='equipo-create'),
    path('equipo/<str:pk>/update/', views.EquipoUpdate.as_view(), name='equipo-update'),
    path('equipo/<str:pk>/delete/', views.EquipoDelete.as_view(), name='equipo-delete'),
    path('equipment/<str:code>/add_supply/', views.add_supply_to_equipment, name='supply'),
    path('transferir-equipo/<str:equipo_id>/', views.transferir_equipo, name='transferir_equipo'),
    path("reportehorasasset/<str:asset_id>/",views.reportHoursAsset,name='horas-asset'),

    path("report-failure/", views.FailureListView.as_view(), name="failure-report-list"),
    path("report-failure/<str:pk>/", views.FailureDetailView.as_view(), name="failure-report-detail"),
    path('report-failure/<str:asset_id>/create/', views.FailureReportForm.as_view(), name='failure-report-create'),
    path('report-failure/<int:pk>/update/', views.FailureReportUpdate.as_view(), name='failure-report-update'),
    path('fail_pdf/<int:pk>/', views.fail_pdf, name='fail_pdf'),
    path('report-failure/<int:fail_id>/crear_ot/', views.crear_ot_failure_report, name='failure-report-crear-ot'),
    path('failure-report/<int:fail_id>/asociar-ot/', views.asociar_ot_failure_report, name='failure-report-asociar-ot'),

    path("ots/", views.OtListView.as_view(), name="ot-list"),
    path("ots/<int:pk>/", views.OtDetailView.as_view(), name="ot-detail"),
    path("ots/create/<str:pk>/", views.OtCreate.as_view(), name="ot-create"),
    path("ots/<int:pk>/update/", views.OtUpdate.as_view(), name="ot-update"),
    path("ots/<int:pk>/delete/", views.OtDelete.as_view(), name="ot-delete"),
    path("report_pdf/<int:num_ot>/", views.ot_pdf, name='report'),

    path("tasks/", views.AssignedTaskByUserListView.as_view(), name="my-tasks"),
    path("task/<int:pk>/", views.TaskDetailView.as_view(), name="task-detail"),
    path('task/<str:pk>/create/', views.TaskCreate.as_view(), name='task-create'),
    path('task/<int:pk>/update/', views.TaskUpdate.as_view(), name='task-update'),
    path('task/<int:pk>/delete/', views.TaskDelete.as_view(), name='task-delete'),
    path('task-rut/<int:pk>/update/', views.TaskUpdaterut.as_view(), name='update-task'),
    path('delete_task/<int:pk>/', views.TaskDeleterut.as_view(), name='delete-task'),
    path('task/<int:pk>/finish/', views.Finish_task.as_view(), name='finish-task'),
    path('task/<int:pk>/finish-ot/', views.Finish_task_ot.as_view(), name='finish-task-ot'),
    path("task/<int:pk>/reschedule/", views.Reschedule_task.as_view(), name='reschedule-task'),

    path('rutas/', views.RutaListView, name="ruta-list"),
    path('ruta/<str:pk>/create/', views.RutaCreate.as_view(), name='ruta-create'),
    path('ruta/<str:pk>/update/', views.RutaUpdate.as_view(), name='ruta-update'),
    path('ruta/<str:pk>/delete/',views.RutaDelete.as_view(), name='ruta-delete'),
    path('ruta/<int:ruta_id>/crear_ot/',views.crear_ot_desde_ruta,name='crear_ot_desde_ruta'),
    path('ruta/<int:ruta_id>/create_ot/', views.rutina_form_view, name='create-ot-from-ruta'),

    path("operations/", views.OperationListView, name="operation-list"),
    path('operation/<int:pk>/update/', views.OperationUpdate.as_view(), name='operation-update'),
    path("operation/<int:pk>/delete/", views.OperationDelete.as_view(), name="operation-delete"),

    path('operation/<int:operation_id>/requirement/add/', views.requirement_create, name='requirement-create'),
    path('requirement/<int:pk>/update/', views.requirement_update, name='requirement-update'),
    path('requirement/<int:pk>/delete/', views.requirement_delete, name='requirement-delete'),

    path('meg/<int:pk>/', views.megger_view, name='meg-detail'),
    path('ots/<int:ot_id>/create_megger/', views.create_megger, name='create_megger'),
    path('meg_pdf/<int:pk>/', views.megger_pdf, name='meg_pdf'),

    path('preoperacional/salidas/', views.SalidaListView.as_view(), name='salidas-consolidado'),
    path("preoperacional/salidas/<int:pk>/", views.SalidaDetailView.as_view(), name="salidas-detail"),
    path('preoperacional/excel/', views.export_preoperacional_to_excel, name='export-preoperacional-excel'),
    path('preoperacional/especifico/<str:code>/', views.preoperacional_especifico_view, name='preoperacional-especifico'),
    path('preoperacional/consolidado/', views.PreoperacionalListView.as_view(), name='preoperacional-consolidado'),
    path('preoperacionaldiario/export/excel/', views.export_preoperacionaldiario_excel, name='export-preoperacionaldiario-excel'),
    path('gracias/<str:code>/', views.gracias_view, name='gracias'),

    path("solicitud/", views.SolicitudesListView.as_view(), name="rq-list"),
    path('solicitud/transfer/<int:pk>/', views.TransferSolicitudView.as_view(), name='transfer-solicitud'),
    path('detalle_pdf/<int:pk>/', views.detalle_pdf, name='solicitud_pdf'),
    path('nueva-solicitud/<str:asset_id>/', views.CreateSolicitudOt.as_view(), name='create-solicitud'),
    path('nueva-solicitud/<str:asset_id>/<int:ot_num>/', views.CreateSolicitudOt.as_view(), name='create-solicitud-ot'),
    path('edit-solicitud/<int:pk>/', views.EditSolicitudView.as_view(), name='edit-solicitud'),
    path('approve-solicitud/<int:pk>/', views.ApproveSolicitudView.as_view(), name='approve-solicitud'),
    path('solicitudes/<int:pk>/report_received/', views.report_received, name='report-received'),
    path('solicitud/update-sc/<int:pk>/', views.update_sc, name='update-sc'),
    path('solicitud/cancel-sc/<int:pk>/', views.cancel_sc, name='cancel-sc'),
    path('solicitudes/download_pdf/', views.download_pdf, name='download_pdf'),

    path("salidas/", views.SalListView.as_view(), name="salida-list"),
    path('salida/create/', views.SalidaCreateView.as_view(), name='create-salida'),
    path('salida/<int:pk>/notify/', views.NotifySalidaView.as_view(), name='notify-salida'),
    path('salida_pdf/<int:pk>/', views.salida_pdf, name='salida_pdf'),
    path('approve-salida/<int:pk>/', views.ApproveSalidaView.as_view(), name='approve-salida'),
    path('salida/<int:pk>/update/', views.SalidaUpdateView.as_view(), name='salida-update'),

    path('items/', views.ItemManagementView.as_view(), name='item_management'),
    path('items/edit/<int:item_id>/', views.edit_item, name='edit_item'),


    path('export/excel/', views.export_asset_system_equipo_excel, name='export_excel'),
    path('equipo/<str:equipo_code>/dar_baja/', views.DarBajaCreateView.as_view(), name='dar_baja'),
    path('manifest.json', views.manifest, name='manifest'),
    path('service-worker.js', views.service_worker, name='service_worker'),
    path('api/unapproved_requests_count/', views.get_unapproved_requests_count, name='unapproved_requests_count_api'),

    path('equipment/<str:equipment_id>/history/', views.EquipmentHistoryView.as_view(), name='equipment_history'),
    path('equipment/<str:equipment_id>/history/add/', views.EquipmentHistoryCreateView.as_view(), name='equipment_history_add'),

    path('equipment/<str:equipment_code>/history/', views.EquipmentHistoryView.as_view(), name='equipment_history'),
    path('equipment/<str:equipment_code>/history/add/', views.EquipmentHistoryCreateView.as_view(), name='equipment_history_add'),
    path('equipment/<str:equipment_code>/history/<int:pk>/edit/', views.EquipmentHistoryUpdateView.as_view(), name='equipment_history_edit'),
    path('equipment/<str:equipment_code>/history/<int:pk>/delete/', views.EquipmentHistoryDeleteView.as_view(), name='equipment_history_delete'),
    
    path('preoperacional/<int:pk>/edit/', views.PreoperacionalUpdateView.as_view(), name='salida-edit'),
]
