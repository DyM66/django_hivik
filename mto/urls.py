from django.urls import path
from .views import *

app_name = 'mto'

urlpatterns = [
    path("report/<str:asset_abbr>/", MaintenancePlanReportView.as_view(), name="plan-report"),
    path('dashboard/<str:asset_abbr>/', MaintenancePlanDashboardView.as_view(), name='dashboard'),
    path("update-plan/<str:asset_abbr>/", update_plan_entries_view, name="update-plan"),
]
