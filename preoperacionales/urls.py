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
    path("success/<str:code>/", views.success_view, name="success"),
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
        "departure_authorization/",
        views.DepartureAuthorizationView.as_view(),
        name="departure_authorization",
    ),
    path(
        "departure_authorization/<str:action>/<str:vehicle_code>/",
        views.DepartureAuthorizationView.as_view(),
        name="departure_authorization_action",
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
    path(
        "delete_vehicle_departure/<int:preoperational_id>/<str:vehicle_code>/",
        views.delete_vehicle_departure,
        name="delete_vehicle_departure",
    ),
    path(
        "edit_vehicle_departure/<int:preoperational_id>/<str:vehicle_code>/",
        views.edit_vehicle_departure,
        name="edit_vehicle_departure",
    ),
]
