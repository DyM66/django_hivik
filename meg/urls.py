from django.urls import path
from . import views

app_name = 'meg'

urlpatterns = [

    path('meg/<int:pk>/', views.megger_view, name='meg-detail'),
    path('create_megger/<int:ot_id>/', views.create_megger, name='create_megger'),
    path('meg_pdf/<int:pk>/', views.megger_pdf, name='meg_pdf'),
]