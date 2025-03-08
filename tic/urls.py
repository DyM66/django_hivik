# tic/urls.py
from django.urls import path
from . import views

app_name = 'tic'

urlpatterns = [
    path('tickets/', views.TicketListView.as_view(), name='ticket-list'),
    path('tickets/create/', views.TicketCreateView.as_view(), name='ticket-create'),
    path('tickets/<int:pk>/', views.TicketDetailView.as_view(), name='ticket-detail'),
    path('tickets/<int:pk>/take/', views.take_ticket, name='ticket-take'),
    path('tickets/<int:pk>/close/', views.close_ticket, name='ticket-close'),
    path('tickets/<int:pk>/update/', views.TicketUpdateView.as_view(), name='ticket-update'),
    path('tickets/<int:pk>/delete/', views.TicketDeleteView.as_view(), name='ticket-delete'),
]
