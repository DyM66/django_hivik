from django.urls import path
from . import views

app_name = 'got'

urlpatterns = [
    path("tasks/", views.AssignedTaskByUserListView.as_view(), name="my-tasks"),

    path("", views.AssetsListView.as_view(), name="asset-list"),
    path("asset/<str:pk>/", views.AssetDetailView.as_view(), name="asset-detail"),
    path('asset/<str:asset_id>/add-document/', views.AssetDocCreateView.as_view(), name='add-document'),
    path('asset/<str:abbreviation>/suministros/', views.asset_suministros_report, name='asset-suministros'),
    path("asset/<str:pk>/schedule/", views.schedule, name="schedule"),
    path('assets/<str:asset_id>/generate-pdf/', views.generate_asset_pdf, name='generate_asset_pdf'),
    
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

    path("reportehoras/<str:component>/", views.reporthours, name='horas'),
    path("reportehorasasset/<str:asset_id>/",views.reportHoursAsset,name='horas-asset'),

    path("report-failure/", views.FailureListView.as_view(), name="failure-report-list"),
    path("report-failure/<str:pk>/", views.FailureDetailView.as_view(), name="failure-report-detail"),
    path('report-failure/<str:asset_id>/create/', views.FailureReportForm.as_view(), name='failure-report-create'),
    path('report-failure/<int:pk>/update/', views.FailureReportUpdate.as_view(), name='failure-report-update'),
    path('report-failure/<int:fail_id>/crear_ot/', views.crear_ot_failure_report, name='failure-report-crear-ot'),
    path('fail_pdf/<int:pk>/', views.fail_pdf, name='fail_pdf'),

    path("ots/", views.OtListView.as_view(), name="ot-list"),
    path("ots/<int:pk>/", views.OtDetailView.as_view(), name="ot-detail"),
    path("ots/create/<str:pk>/", views.OtCreate.as_view(), name="ot-create"),
    path("ots/<int:pk>/update/", views.OtUpdate.as_view(), name="ot-update"),
    path("ots/<int:pk>/delete/", views.OtDelete.as_view(), name="ot-delete"),
    path("report_pdf/<int:num_ot>/", views.ot_pdf, name='report'),

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
    path('buceo/', views.buceomtto, name='buceomtto'),

    path("operations/", views.OperationListView, name="operation-list"),
    path('operation/<int:pk>/update/', views.OperationUpdate.as_view(), name='operation-update'),
    path("operation/<int:pk>/delete/", views.OperationDelete.as_view(), name="operation-delete"),

    path('meg/<int:pk>/', views.megger_view, name='meg-detail'),
    path('ots/<int:ot_id>/create_megger/', views.create_megger, name='create_megger'),
    path('meg_pdf/<int:pk>/', views.megger_pdf, name='meg_pdf'),

    path('preoperacional/salidas/', views.SalidaListView.as_view(), name='salidas-consolidado'),
    path("preoperacional/salidas/<int:pk>/", views.SalidaDetailView.as_view(), name="salidas-detail"),
    path('preoperacional/especifico/<str:code>/', views.preoperacional_especifico_view, name='preoperacional-especifico'),

    path('preoperacional/consolidado/', views.PreoperacionalListView.as_view(), name='preoperacional-consolidado'),
    path("preoperacional/consolidado/<int:pk>/", views.PreoperacionalDetailView.as_view(), name="preoperacional-detail"),
    path('preoperacional/diario/<str:code>/', views.preoperacional_diario_view, name='preoperacional-dia'),
    path('gracias/<str:code>/', views.gracias_view, name='gracias'),

    path("solicitud/", views.SolicitudesListView.as_view(), name="rq-list"),
    path('detalle_pdf/<int:pk>/', views.detalle_pdf, name='solicitud_pdf'),
    path('nueva-solicitud/<str:asset_id>/', views.CreateSolicitudOt.as_view(), name='create-solicitud'),
    path('nueva-solicitud/<str:asset_id>/<int:ot_num>/', views.CreateSolicitudOt.as_view(), name='create-solicitud-ot'),
    path('edit-solicitud/<int:pk>/', views.EditSolicitudView.as_view(), name='edit-solicitud'),
    path('approve-solicitud/<int:pk>/', views.ApproveSolicitudView.as_view(), name='approve-solicitud'),
    path('solicitud/update-sc/<int:pk>/', views.update_sc, name='update-sc'),
    path('solicitud/cancel-sc/<int:pk>/', views.cancel_sc, name='cancel-sc'),
    path('solicitudes/download_pdf/', views.download_pdf, name='download_pdf'),

    path("salidas/", views.SalListView.as_view(), name="salida-list"),
    path('salida/create/', views.SalidaCreateView.as_view(), name='create-salida'),
    path('approve-salida/<int:pk>/', views.ApproveSalidaView.as_view(), name='approve-salida'),
    path('salida_pdf/<int:pk>/', views.salida_pdf, name='salida_pdf'),

    path("dash/", views.indicadores, name='dashboard'),

    path('add-location/', views.add_location, name='add-location'),
    path('location/<int:pk>/', views.view_location, name='view-location'),

    path('items/', views.ItemManagementView.as_view(), name='item_management'),
    path('items/edit/<int:item_id>/', views.edit_item, name='edit_item'),
    path('asset/rutinas/<str:pk>/', views.preventivo_pdf, name='preventivo'),

    path('ruta/<int:ruta_id>/create_ot/', views.rutina_form_view, name='create-ot-from-ruta'),
    path('salida/<int:pk>/notify/', views.NotifySalidaView.as_view(), name='notify-salida'),
    path('salida/<int:pk>/update/', views.SalidaUpdateView.as_view(), name='salida-update'),
    path('preoperacional/excel/', views.export_preoperacional_to_excel, name='export-preoperacional-excel'),
    path('preoperacionaldiario/export/excel/', views.export_preoperacionaldiario_excel, name='export-preoperacionaldiario-excel'),
]
