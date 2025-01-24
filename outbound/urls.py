from django.urls import path
from . import views

app_name = 'outbound'

urlpatterns = [
    path("salidas/", views.OutboundListView.as_view(), name="outbound-list"),
    path('create/', views.SalidaCreateView.as_view(), name='create-salida'),

    path('salida/<int:pk>/notify/', views.NotifySalidaView.as_view(), name='notify-salida'),
    path('salida_pdf/<int:pk>/', views.salida_pdf, name='salida_pdf'),
    path('approve-salida/<int:pk>/', views.ApproveSalidaView.as_view(), name='approve-salida'),
    path('salida/<int:pk>/update/', views.SalidaUpdateView.as_view(), name='salida-update'),

    path('places/', views.PlaceListView.as_view(), name='place-list'),
    path('places/create/', views.PlaceCreateView.as_view(), name='place-create'),
    path('places/<int:pk>/update/', views.PlaceUpdateView.as_view(), name='place-update'),
    path('places/<int:pk>/delete/', views.PlaceDeleteView.as_view(), name='place-delete'),
]