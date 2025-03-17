# ntf/urls.py
from django.urls import path
from .views import *

app_name = "ntf"

urlpatterns = [
    path('notifications/', get_notifications, name='get_notifications'),
    path('notifications/mark_seen/', mark_notification_seen, name='mark_notification_seen'),
]
