from django.urls import path
from . import views

app_name = 'preoperacionales'

urlpatterns = [
    path("detail/<int:pk>/", views.PreoperacionalDetailView.as_view(), name="preoperacional-detail"),
    path("diario/<str:code>/", views.preoperacional_diario_view, name='preoperacional-dia'),
    path("editar/<int:pk>/", views.PreoperacionalDiarioUpdateView.as_view(), name="preoperacional-edit"),
    path("salidas/", views.SalidaListView.as_view(), name='salidas-consolidado'),
    path("salidas/<int:pk>/", views.SalidaDetailView.as_view(), name="salidas-detail"),


    path('excel/', views.export_preoperacional_to_excel, name='export-preoperacional-excel'),
    path('preoperacional/<str:code>/', views.preoperacional_especifico_view, name='preoperacional-especifico'),
    path('consolidado/', views.PreoperacionalListView.as_view(), name='preoperacional-consolidado'),
    path('preoperacionaldiario/export/excel/', views.export_salidas_to_excel, name='export-preoperacionaldiario-excel'),
    path('gracias/<str:code>/', views.gracias_view, name='gracias'),
    path('preoperacional/<int:pk>/edit/', views.PreoperacionalUpdateView.as_view(), name='salida-edit'),
]