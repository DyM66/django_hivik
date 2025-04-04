from django.urls import path
from dth import views
from dth.views import docs_matrix_views

app_name = 'dth'

urlpatterns = [
    path('perfil/', views.profile_update, name='profile_update'),
    path('toggle_view_mode/', views.toggle_view_mode, name='toggle_view_mode'),

    # overtime_views
	path('', views.OvertimeListView.as_view(), name='overtime_list'),
    path('approve/', views.approve_overtime, name='approve_overtime'),
    path('edit-overtime/', views.edit_overtime, name='edit_overtime'),
    path('delete-overtime/', views.delete_overtime, name='delete_overtime'),
    path('buscar-nomina/', views.buscar_nomina, name='buscar_nomina'),
    path('crear-overtime/', views.OvertimeProjectCreateView.as_view(), name='overtime_report'),
    path('export_excel/', views.export_overtime_excel, name='export_overtime_excel'),

    #payroll_report_views
    path('gerencia/nomina/', views.gerencia_nomina_view, name='gerencia_nomina'),
    path('gerencia/nomina/export/', views.export_gerencia_nomina_excel, name='gerencia_nomina_export'),

    # payroll_views
    path('payroll/', views.NominaListView.as_view(), name='nomina_list'),
    path('api/nomina/<int:pk>/detail/', views.nomina_detail_partial, name='nomina_detail_partial'),
    path('nomina/create/', views.nomina_create, name='nomina_create'),
    path('payroll/<int:pk>/update/', views.NominaUpdateView.as_view(), name='nomina_update'),
    path('nomina/<int:pk>/edit/', views.nomina_edit, name='nomina_edit'),

    # Job Profile Views
    path('edit_document/<int:doc_id>/', views.edit_document, name='edit_document'),
    path('delete_document/<int:doc_id>/', views.delete_document, name='delete_document'),
    path('positions/create/', views.create_position, name='create_position'),
    path('edit_position/<int:position_id>/', views.edit_position, name='edit_position'),
    path('delete_position/<int:position_id>/', views.delete_position, name='delete_position'),
    path('create_position_document/', views.create_position_document, name='create_position_document'),
    path('delete_position_document/', views.delete_position_document, name='delete_position_document'),
    path('position_documents_list/', views.JobProfileListView.as_view(), name='position_documents_list'),

	# Document Matrix Views
    path('nomina/documents_matrix/', views.nomina_documents_matrix, name='nomina_documents_matrix'),
	path('employee_document_form/', docs_matrix_views.upload_employee_document, name='employee_document_form'),
    path('create_employee_document/', docs_matrix_views.create_employee_document, name='create_employee_document'),
    path('employee_document_preview/', docs_matrix_views.employee_document_preview, name='employee_document_preview'),
    path('delete_employee_document/', docs_matrix_views.delete_employee_document, name='delete_employee_document'),
    # Funcionalidad para solicitar documentos
    path('document-upload/<str:token>/', views.document_upload_view, name='document_upload_view'),
    path('document-upload/success/', views.document_upload_success, name='document_upload_success'),

	path('reject-document/', views.reject_document_request_item, name='reject_document_request_item'),

    path('request_docs_form/<int:emp_id>/', views.request_docs_form, name='request_docs_form'),
    path('request_docs_submit/', views.request_docs_submit, name='request_docs_submit'),

    path('admin/docs/requests/', views.admin_document_request_list, name='admin_document_request_list'),
    path('admin/docs/requests/<int:pk>/', views.admin_document_request_detail, name='admin_document_request_detail'),
    
	path('document-upload-partial/', views.document_upload_partial, name='document_upload_partial'),
]
