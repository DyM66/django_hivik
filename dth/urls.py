from django.urls import path
from dth import views

app_name = 'dth'

urlpatterns = [
    path('perfil/', views.profile_update, name='profile_update'),

    path('', views.OvertimeListView.as_view(), name='overtime_list'),
    path('approve/<int:pk>/', views.approve_overtime, name='approve_overtime'),
    path('edit/<int:pk>/', views.edit_overtime, name='edit_overtime'),
    path('delete/<int:pk>/', views.delete_overtime, name='delete_overtime'),
    path('export_excel/', views.export_overtime_excel, name='export_overtime_excel'),
    path('report/', views.overtime_report, name='overtime_report'),
    path('success/', views.overtime_success, name='overtime_success'),
]
