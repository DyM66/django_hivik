from django.urls import path
from dth import views

app_name = 'dth'

urlpatterns = [
    path('perfil/', views.profile_update, name='profile_update'),

    path('', views.OvertimeListView.as_view(), name='overtime_list'),
    path('approve/', views.approve_overtime, name='approve_overtime'),

    path('crear-overtime/', views.create_overtime_report, name='overtime_report'),
    path('buscar-nomina/', views.buscar_nomina, name='buscar_nomina'),

    path('edit-overtime/', views.edit_overtime, name='edit_overtime'),
    path('delete-overtime/', views.delete_overtime, name='delete_overtime'),
    path('export_excel/', views.export_overtime_excel, name='export_overtime_excel'),

    path('gerencia/nomina/', views.gerencia_nomina_view, name='gerencia_nomina'),
    path('gerencia/nomina/export/', views.export_gerencia_nomina_excel, name='gerencia_nomina_export'),

    path('nomina/<int:pk>/edit/', views.nomina_edit, name='nomina_edit'),
    path('nomina/create/', views.nomina_create, name='nomina_create'),
]
