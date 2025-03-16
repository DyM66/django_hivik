# ntf/urls.py
from django.urls import path
from .views import *

app_name = "ntf"

urlpatterns = [
    path('guardar-suscripcion/', save_push_subscription, name="save_push_subscription"),
    path('test-notificacion/', test_push_notification, name="test_push_notification"),
]
