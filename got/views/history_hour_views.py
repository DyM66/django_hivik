from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from datetime import timedelta, date, datetime
from django.contrib import messages
from django.urls import reverse

from got.models.asset import Asset
from got.models.equipment import Equipo
from got.models.history_hour import HistoryHour

@login_required
def reportHoursAsset(request, asset_id):
    asset = get_object_or_404(Asset, pk=asset_id)
    today = date.today()
    dates = [today - timedelta(days=x) for x in range(90)]
    equipos_rotativos = Equipo.objects.filter(system__in=asset.system_set.all(), type__code='r')

    if request.method == 'POST':
        equipo_id = request.POST.get('equipo_id')
        report_date = request.POST.get('report_date')
        hour = request.POST.get('hour')
        hist_id = request.POST.get('hist_id')

        try:
            hour_value = float(hour)
            fecha = datetime.strptime(report_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            messages.error(request, "Datos inválidos para actualizar horas (formato de fecha u horas).")
            return redirect(reverse('got:horas-asset', args=[asset_id]))

        # Validar rangos de hora
        if hour_value < 0 or hour_value > 24:
            messages.error(request, "El valor de horas debe estar entre 0 y 24.")
            return redirect(request.META.get('HTTP_REFERER', reverse('got:horas-asset', args=[asset_id])))
            
        # Buscar o crear HistoryHour
        equipo = get_object_or_404(Equipo, pk=equipo_id)
        # Verificamos si hist_id es un entero válido
        try:
            hist_id_int = int(hist_id)  # si hist_id es None, "" o "None", lanzará ValueError
            history_hour = get_object_or_404(HistoryHour, pk=hist_id_int)
        except (TypeError, ValueError):
            # hist_id no es un entero válido => creamos un nuevo registro
            history_hour = HistoryHour(component=equipo)

        history_hour.hour = hour_value
        history_hour.report_date = fecha
        history_hour.reporter = request.user
        history_hour.modified_by = request.user
        history_hour.save()

        messages.success(request, "Horas actualizadas correctamente.")
        return redirect(reverse('got:horas-asset', args=[asset_id]))

    # --------------------------------------------------------------------------
    # 2. Construir la información (equipos_data y transposed_data) para la tabla
    # --------------------------------------------------------------------------
    equipos_data = []
    for equipo in equipos_rotativos:
        # Diccionario con fecha -> {hour, reporter, hist_id}
        horas_reportadas = {}
        for d in dates:
            horas_reportadas[d] = {
                'hour': 0,
                'reporter': None,
                'hist_id': None
            }

        # Consulta de HistoryHour existentes
        registros = HistoryHour.objects.filter(component=equipo, report_date__range=(dates[-1], today)).select_related('reporter')

        for reg in registros:
            if reg.report_date in horas_reportadas:
                horas_reportadas[reg.report_date]['hour'] = reg.hour
                horas_reportadas[reg.report_date]['reporter'] = (reg.reporter.username if reg.reporter else None)
                horas_reportadas[reg.report_date]['hist_id'] = reg.id

        # Crear lista en el mismo orden que `dates`
        lista_horas = [horas_reportadas[d] for d in dates]

        equipos_data.append({
            'equipo': equipo,
            'horas': lista_horas,
        })

    context = {
        'asset': asset,
        'equipos_data': equipos_data,
        'dates': dates,
    }
    return render(request, 'got/assets/hours_asset.html', context)
