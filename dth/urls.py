from django.urls import path
from dth import views
from dth.views import payroll_docs_views

app_name = 'dth'

urlpatterns = [
    path('perfil/', views.profile_update, name='profile_update'),

    path('', views.OvertimeListView.as_view(), name='overtime_list'), # Check
    path('approve/', views.approve_overtime, name='approve_overtime'), # Check
    path('edit-overtime/', views.edit_overtime, name='edit_overtime'), # Check
    path('delete-overtime/', views.delete_overtime, name='delete_overtime'),# Check
    path('buscar-nomina/', views.buscar_nomina, name='buscar_nomina'), # Check
    path('crear-overtime/', views.OvertimeProjectCreateView.as_view(), name='overtime_report'), # Check


    path('export_excel/', views.export_overtime_excel, name='export_overtime_excel'),

    path('gerencia/nomina/', views.gerencia_nomina_view, name='gerencia_nomina'),
    path('gerencia/nomina/export/', views.export_gerencia_nomina_excel, name='gerencia_nomina_export'),
    path('nomina/create/', views.nomina_create, name='nomina_create'),

    path('payroll/', views.NominaListView.as_view(), name='nomina_list'),
    path('payroll/<int:pk>/update/', views.NominaUpdateView.as_view(), name='nomina_update'),
    path('api/nomina/<int:pk>/detail/', views.nomina_detail_partial, name='nomina_detail_partial'),
    path('positions/create/', views.create_position, name='create_position'),

    path('toggle_view_mode/', views.toggle_view_mode, name='toggle_view_mode'),
    path('edit_position/<int:position_id>/', views.edit_position, name='edit_position'),
    path('delete_position/<int:position_id>/', views.delete_position, name='delete_position'),

    path('position_documents_list/', views.PositionDocumentListView.as_view(), name='position_documents_list'),

    path('create_position_document/', views.create_position_document, name='create_position_document'),
    path('delete_position_document/', views.delete_position_document, name='delete_position_document'),

    path('edit_document/<int:doc_id>/', views.edit_document, name='edit_document'),
    path('delete_document/<int:doc_id>/', views.delete_document, name='delete_document'),

    path('nomina/<int:pk>/edit/', views.nomina_edit, name='nomina_edit'),

    path('nomina/documents_matrix/', views.nomina_documents_matrix, name='nomina_documents_matrix'),

    path('employee_document_form/', payroll_docs_views.employee_document_form, name='employee_document_form'),
    path('create_employee_document/', payroll_docs_views.create_employee_document, name='create_employee_document'),
    path('employee_document_preview/', payroll_docs_views.employee_document_preview, name='employee_document_preview'),
    path('delete_employee_document/', payroll_docs_views.delete_employee_document, name='delete_employee_document'),

    path('document-upload/<str:token>/', views.document_upload_view, name='document_upload_view'),
]
