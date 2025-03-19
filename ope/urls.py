from django.urls import path
from .views import *

app_name = 'ope'

urlpatterns = [
    path("operations/", OperationListView.as_view(), name="operation-list"),
    path('operation/<int:pk>/update/', update_operation, name='operation_update'),
    path("operation/<int:pk>/delete/", OperationDelete.as_view(), name="operation-delete"),
    path('operation/<int:operation_id>/requirement/add/', requirement_create, name='requirement-create'),
    path('requirement/<int:pk>/update/', requirement_update, name='requirement-update'),
    path('requirement/<int:pk>/delete/', requirement_delete, name='requirement-delete'),
]
