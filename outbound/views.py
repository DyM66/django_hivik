from django.shortcuts import render
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import *


class OutboundListView(LoginRequiredMixin, generic.ListView):

    model = OutboundDelivery
    paginate_by = 20
    template_name = 'outbound/salidas_list.html'

    def get_queryset(self):
        queryset = super().get_queryset()
        destino = self.request.GET.get('destino', '').strip()
        fecha = self.request.GET.get('fecha', '').strip()
        motivo = self.request.GET.get('motivo', '').strip()
        propietario = self.request.GET.get('propietario', '').strip()
        adicional = self.request.GET.get('adicional', '').strip()

        if destino:
            queryset = queryset.filter(destino__icontains=destino)
        if fecha:
            queryset = queryset.filter(fecha=fecha)  # Fecha en formato 'YYYY-MM-DD'
        if motivo:
            queryset = queryset.filter(motivo__icontains=motivo)
        if propietario:
            queryset = queryset.filter(propietario__icontains=propietario)
        if adicional:
            queryset = queryset.filter(adicional__icontains=adicional)
        return queryset
