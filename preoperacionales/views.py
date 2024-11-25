
from datetime import datetime, time, date
from django.db.models import Sum
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.views import generic, View
from django.urls import reverse
from django.utils.timezone import localdate
from .models import *
from .forms import *
from got.forms import UploadImages
from got.models import Equipo, HistoryHour, Image


class PreoperacionalDetailView(LoginRequiredMixin, generic.DetailView):

    model = PreoperacionalDiario
    template_name = 'preoperacional/preoperacional_detail.html'


def preoperacional_diario_view(request, code):
    
    equipo = get_object_or_404(Equipo, code=code)
    rutas_vencidas = [ruta for ruta in equipo.equipos.all() if ruta.next_date < date.today()]

    existente = PreoperacionalDiario.objects.filter(vehiculo=equipo, fecha=localdate()).first()

    if existente:
        mensaje = f"El preoperacional del vehículo {equipo} de la fecha actual ya fue diligenciado y exitosamente enviado. El resultado fue: {'Aprobado' if existente.aprobado else 'No aprobado'}."
        messages.error(request, mensaje)
        return render(request, 'preoperacional/preoperacional_restricted.html', {'mensaje': mensaje})
    
    if request.method == 'POST':
        form = PreoperacionalDiarioForm(request.POST, equipo_code=equipo.code, user=request.user)
        image_form = UploadImages(request.POST, request.FILES)
        if form.is_valid() and image_form.is_valid():
            preop = form.save(commit=False)
            preop.reporter = request.user if request.user.is_authenticated else None
            preop.vehiculo = equipo
            preop.kilometraje = form.cleaned_data['kilometraje']
            preop.save()

            horometro_actual = equipo.initial_hours + (equipo.hours.filter(report_date__lt=localdate()).aggregate(total=Sum('hour'))['total'] or 0)
            kilometraje_reportado = preop.kilometraje - horometro_actual

            history_hour, created = HistoryHour.objects.get_or_create(
                component=equipo,
                report_date=localdate(),
                defaults={'hour': kilometraje_reportado}
            )

            if not created:
                history_hour.hour = kilometraje_reportado
                history_hour.save()

            equipo.horometro = preop.kilometraje
            equipo.save()

            for file in request.FILES.getlist('file_field'):
                Image.objects.create(preoperacional=preop, image=file)

            return redirect('got:gracias', code=equipo.code) 
    else:
        form = PreoperacionalDiarioForm(equipo_code=equipo.code, user=request.user)
        image_form = UploadImages()

    return render(request, 'preoperacional/preoperacionalform.html', {'vehiculo': equipo, 'form': form, 'image_form': image_form, 'rutas_vencidas': rutas_vencidas, 'pre': True})


class PreoperacionalDiarioUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = PreoperacionalDiario
    form_class = PreoperacionalDiarioForm
    template_name = 'preoperacional/preoperacionalform.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        preoperacional = self.get_object()
        kwargs['equipo_code'] = preoperacional.vehiculo.code
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        preoperacional = form.instance
        equipo = preoperacional.vehiculo
        fecha_preoperacional = preoperacional.fecha
        horometro_actual = equipo.initial_hours + (
            equipo.hours.exclude(report_date=fecha_preoperacional).aggregate(total=Sum('hour'))['total'] or 0
        )
        kilometraje_reportado = form.cleaned_data['kilometraje'] - horometro_actual

        history_hour, _ = HistoryHour.objects.get_or_create(
            component=equipo,
            report_date=preoperacional.fecha,
            defaults={'hour': kilometraje_reportado}
        )

        history_hour.hour = kilometraje_reportado
        history_hour.save()

        equipo.horometro = form.cleaned_data['kilometraje']
        equipo.save()

        return response

    def get_success_url(self):
        return reverse('preoperacionales:preoperacional-detail', kwargs={'pk': self.object.pk})