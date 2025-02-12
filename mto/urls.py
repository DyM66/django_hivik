from django.urls import path
from .views import *

app_name = 'mto'

urlpatterns = [
    path("report/<str:asset_abbr>/", MaintenancePlanReportView.as_view(), name="plan-report"),
]
