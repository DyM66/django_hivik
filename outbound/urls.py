from django.urls import path
from . import views

app_name = 'outbound'

urlpatterns = [
    path("salidas/", views.OutboundListView.as_view(), name="outbound-list"),

]