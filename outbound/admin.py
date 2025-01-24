# outbound/admin.py

from django.contrib import admin
from .models import Place, OutboundDelivery

@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'latitude', 'longitude')
    search_fields = ('name', 'city')

@admin.register(OutboundDelivery)
class OutboundDeliveryAdmin(admin.ModelAdmin):
    list_display = ('motivo', 'fecha', 'propietario', 'responsable', 'recibe', 'vehiculo', 'auth', 'destination')
    list_filter = ('auth', 'fecha')
    search_fields = ('motivo', 'propietario', 'responsable', 'recibe', 'vehiculo')
    autocomplete_fields = ('destination',)
