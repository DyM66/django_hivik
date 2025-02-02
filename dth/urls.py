from django.urls import path
from dth import views

app_name = 'dth'

urlpatterns = [
    path('perfil/', views.profile_update, name='profile_update'),
]
