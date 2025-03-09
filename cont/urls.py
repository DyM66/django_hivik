# con/urls.py
from django.urls import path
from .views import *

app_name = 'con'

urlpatterns = [
    path('financiacion/nuevo/<int:asset_cost_pk>/', FinanciacionCreateView.as_view(), name='financiacion-create'),
    path('', AssetCostListView.as_view(), name='asset-list'),
    path('asset/<int:pk>/', AssetCostDetailView.as_view(), name='asset-detail'),
    path('assetcost/<int:pk>/update/', update_assetcost, name='assetcost-update'),
    path('gastos/upload/ajax/', gastos_upload_ajax, name='gastos-upload-ajax'),
]
