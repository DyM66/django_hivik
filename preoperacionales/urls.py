from django.urls import path
from . import views

app_name = 'preoperacionales'

urlpatterns = [
    path("detail/<int:pk>/", views.PreoperacionalDetailView.as_view(), name="preoperacional-detail"),
    path('diario/<str:code>/', views.preoperacional_diario_view, name='preoperacional-dia'),
    path("editar/<int:pk>/", views.PreoperacionalDiarioUpdateView.as_view(), name="preoperacional-edit"),

]