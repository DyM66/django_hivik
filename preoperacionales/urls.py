from django.urls import path
from . import views

app_name = "preoperacionales"

urlpatterns = [
    path(
        "detail/<int:pk>/",
        views.PreoperacionalDetailView.as_view(),
        name="preoperacional-detail",
    ),
    path(
        "diario/<str:code>/",
        views.preoperacional_diario_view,
        name="preoperacional-dia",
    ),
    path(
        "editar/<int:pk>/",
        views.PreoperacionalDiarioUpdateView.as_view(),
        name="preoperacional-edit",
    ),
    path("salidas/", views.SalidaListView.as_view(), name="salidas-consolidado"),
    path("salidas/<int:pk>/", views.SalidaDetailView.as_view(), name="salidas-detail"),
    path(
        "excel/",
        views.export_preoperacional_to_excel,
        name="export-preoperacional-excel",
    ),
    path(
        "especifico/<str:code>/",
        views.preoperacional_especifico_view,
        name="preoperacional-especifico",
    ),
    path(
        "consolidado/",
        views.PreoperacionalListView.as_view(),
        name="preoperacional-consolidado",
    ),
    path(
        "preoperacionaldiario/export/excel/",
        views.export_salidas_to_excel,
        name="export-preoperacionaldiario-excel",
    ),
    path("gracias/<str:code>/", views.gracias_view, name="gracias"),
    path(
        "preoperacional/<int:pk>/edit/",
        views.PreoperacionalUpdateView.as_view(),
        name="salida-edit",
    ),
    path(
        "public-vehicles/",
        views.PublicVehicleMenuView.as_view(),
        name="public_vehicle_menu",
    ),
    path(
        "preoperational_authorization/",
        views.PreoperationalAuthorizationView.as_view(),
        name="preoperational_authorization",
    ),
    path(
        "preoperational_authorization/<str:action>/<str:vehicle_code>/",
        views.PreoperationalAuthorizationView.as_view(),
        name="preoperational_authorization_action",
    ),
    path(
        "admin/",
        views.AdminView.as_view(),
        name="admin",
    ),
    path(
        "admin/<str:vehicle_code>/",
        views.VehicleAdminView.as_view(),
        name="vehicle_admin",
    ),
    path(
        "admin/<str:vehicle_code>/<str:action>/",
        views.VehicleAdminView.as_view(),
        name="vehicle_action",
    ),
]
