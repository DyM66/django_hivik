from django.urls import path
from . import views
from got import pwa

app_name = 'got'

urlpatterns = [
    path("", views.AssetsListView.as_view(), name="asset-list"),
    path("asset/<str:pk>/", views.AssetDetailView.as_view(), name="asset-detail"),
    path('asset/<str:abbreviation>/documents/', views.AssetDocumentsView.as_view(), name='asset-documents'),
    path('document/<int:pk>/edit/', views.edit_document, name='edit-document'),
    path('document/<int:pk>/delete/', views.delete_document, name='delete-document'),

    path("systems/<int:pk>/", views.SysDetailView.as_view(), name="sys-detail"),
    path('system/<int:pk>/update/', views.SysUpdate.as_view(), name='sys-update'),
    path('system/<int:pk>/delete/', views.SysDelete.as_view(), name='sys-delete'),
    
    path('Equipment/<str:pk>/', views.EquipoDetailView.as_view(), name='equipo-detail'),
    path('system/<int:pk>/new_equipo/', views.EquipoCreateView.as_view(), name='equipo-create'),
    path('equipo/<str:pk>/update/', views.EquipoUpdate.as_view(), name='equipo-update'),
    path('equipo/<str:pk>/delete/', views.EquipoDelete.as_view(), name='equipo-delete'),
    path('equipment/<str:code>/add_supply/', views.add_supply_to_equipment, name='supply'),
    path('equipo/<pk>/delete_image/', views.EquipoDeleteImageView.as_view(), name='equipo-delete-image'),

    path("reportehorasasset/<str:asset_id>/",views.reportHoursAsset,name='horas-asset'),
    path('ruta/<int:pk>/', views.RutaDetailView.as_view(), name='ruta_detail'),
    path('ruta/<str:pk>/create/', views.RutaCreate.as_view(), name='ruta-create'),
    path('ruta/<str:pk>/update/', views.RutaUpdate.as_view(), name='ruta-update'),
    path('ruta/<str:pk>/delete/',views.RutaDelete.as_view(), name='ruta-delete'),

    path('asset/acta/<str:pk>/', views.acta_entrega_pdf, name='acta_entrega'),
    path('got/budget/summary/assets/<str:asset_id>/pdf/', views.asset_maintenance_pdf, name='asset_maintenance_pdf'),

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
    path('tasks/excel/', views.assignedTasks_excel, name='assigned-tasks-excel'),
    path('tasks/pdf/', views.assignedTasks_pdf, name='assigned-tasks-pdf'),
    path('task/<str:pk>/create/', views.TaskCreate.as_view(), name='task-create'),
    path('task/<int:pk>/update/', views.TaskUpdate.as_view(), name='task-update'),
    path('task/<int:pk>/delete/', views.TaskDelete.as_view(), name='task-delete'),
    path('delete_task/<int:pk>/', views.TaskDeleterut.as_view(), name='delete-task'),
    path('task/<int:pk>/finish/', views.Finish_task.as_view(), name='finish-task'),
    path('task/<int:pk>/finish-ot/', views.Finish_task_ot.as_view(), name='finish-task-ot'),
    path("task/<int:pk>/reschedule/", views.Reschedule_task.as_view(), name='reschedule-task'),

    path('rutas/', views.RutaListView, name="ruta-list"), # No se esta usando

    path('ruta/<int:ruta_id>/crear_ot/',views.crear_ot_desde_ruta,name='crear_ot_desde_ruta'),
    path('ruta/<int:ruta_id>/create_ot/', views.rutina_form_view, name='create-ot-from-ruta'),

    path("operations/", views.OperationListView, name="operation-list"),
    path('operation/<int:pk>/update/', views.OperationUpdate.as_view(), name='operation-update'),
    path("operation/<int:pk>/delete/", views.OperationDelete.as_view(), name="operation-delete"),
    path('operation/<int:operation_id>/requirement/add/', views.requirement_create, name='requirement-create'),
    path('requirement/<int:pk>/update/', views.requirement_update, name='requirement-update'),
    path('requirement/<int:pk>/delete/', views.requirement_delete, name='requirement-delete'),

    path("solicitud/", views.SolicitudesListView.as_view(), name="rq-list"),
    path('detalle_pdf/<int:pk>/', views.detalle_pdf, name='solicitud_pdf'),
    path('nueva-solicitud/<str:asset_id>/', views.CreateSolicitudOt.as_view(), name='create-solicitud'),
    path('nueva-solicitud/<str:asset_id>/<int:ot_num>/', views.CreateSolicitudOt.as_view(), name='create-solicitud-ot'),
    path('edit-solicitud/<int:pk>/', views.EditSolicitudView.as_view(), name='edit-solicitud'),
    path('approve-solicitud/<int:pk>/', views.ApproveSolicitudView.as_view(), name='approve-solicitud'),
    path('solicitud/<int:pk>/delete/', views.DeleteSolicitudView.as_view(), name='delete-solicitud'),
    path('solicitudes/<int:pk>/report_received/', views.report_received, name='report-received'),
    path('solicitud/update-sc/<int:pk>/', views.update_sc, name='update-sc'),
    path('solicitud/cancel-sc/<int:pk>/', views.cancel_sc, name='cancel-sc'),
    path('solicitudes/download_pdf/', views.download_pdf, name='download_pdf'),
    path('solicitud/transfer/<int:pk>/', views.TransferSolicitudView.as_view(), name='transfer-solicitud'),

    path("dash/", views.indicadores, name='dashboard'),

    path('mantenimiento/', views.MaintenanceDashboardView.as_view(), name='maintenance_dashboard'),
    path('budget/', views.BudgetView.as_view(), name='budget_view'),
    path('budget/summary/assets/', views.BudgetSummaryByAssetView.as_view(), name='budget_summary_by_asset'),

    path('managerial-report/<str:abbreviation>/', views.managerial_asset_report_pdf, name='managerial_asset_report'),
    path('manifest.json', pwa.manifest, name='manifest'),
    path('service-worker.js', pwa.service_worker, name='service_worker'),
    path('api/unapproved_requests_count/', pwa.get_unapproved_requests_count, name='unapproved_requests_count_api'),

    path('maintenance-plan/export/<str:asset_abbr>/', views.MaintenancePlanExcelExportView.as_view(), name='maintenance_plan_excel_export'),

    path('notifications/', views.get_notifications, name='get_notifications'),
    path('notifications/mark_seen/', views.mark_notification_seen, name='mark_notification_seen'),

    path('assets/<str:pk>/pdf/', views.EquipoPDFView.as_view(), name='equipo-pdf'),

    path('ot/<int:ot_num>/download_task_images/', views.download_ot_task_images, name='download_ot_task_images'),
]