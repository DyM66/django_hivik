from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import permission_required, login_required
from django.utils.http import url_has_allowed_host_and_scheme
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from datetime import date
from itertools import groupby
from dateutil.relativedelta import relativedelta
from operator import attrgetter
from django.core.paginator import Paginator
from .models import *
from .forms import *
import openpyxl
from openpyxl.utils import get_column_letter
from django.http import HttpResponse
from datetime import datetime, time, date


class OvertimeListView(LoginRequiredMixin, ListView):
    model = Overtime
    template_name = 'overtime/overtime_list.html'
    context_object_name = 'overtime_entries'
    paginate_by = 25

    def get_queryset(self):
        person_name = self.request.GET.get('person_name', '')
        asset_name = self.request.GET.get('asset', '')
        date_filter = self.request.GET.get('date', '')
        aprobado_filter = self.request.GET.get('aprobado', 'all')

        today = date.today()

        if today.day < 24:
            start_date = (today - relativedelta(months=1)).replace(day=24)
            end_date = today.replace(day=24)
        else:
            start_date = today.replace(day=24)
            end_date = (today + relativedelta(months=1)).replace(day=24)

        overtime_entries = Overtime.objects.filter(fecha__gte=start_date, fecha__lt=end_date)

        if person_name:
            overtime_entries = overtime_entries.filter(nombre_completo__icontains=person_name)

        if asset_name:
            overtime_entries = overtime_entries.filter(asset__name__icontains=asset_name)

        if date_filter:
            overtime_entries = overtime_entries.filter(fecha=date_filter)

        if aprobado_filter == 'aprobado':
            overtime_entries = overtime_entries.filter(approved=True)
        elif aprobado_filter == 'no_aprobado':
            overtime_entries = overtime_entries.filter(approved=False)

        overtime_entries = overtime_entries.order_by('-fecha', 'asset', 'justificacion')

        return overtime_entries

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page_obj = context['page_obj']

        date_asset_justification_groups = []

        for fecha, fecha_entries in groupby(page_obj.object_list, key=attrgetter('fecha')):
            asset_groups = []
            fecha_entries = list(fecha_entries)
            for asset, asset_entries in groupby(fecha_entries, key=attrgetter('asset')):
                asset_entries = list(asset_entries)
                for justificacion, justificacion_entries in groupby(asset_entries, key=attrgetter('justificacion')):
                    justificacion_entries = list(justificacion_entries)
                    asset_groups.append({
                        'asset': asset,
                        'justificacion': justificacion,
                        'entries': justificacion_entries
                    })
            date_asset_justification_groups.append({
                'fecha': fecha,
                'assets': asset_groups
            })

        context['date_asset_groups'] = date_asset_justification_groups
        return context


@login_required
@permission_required('got.can_approve_overtime', raise_exception=True)
def approve_overtime(request, pk):
    if request.method == 'POST':
        overtime_entry = get_object_or_404(Overtime, pk=pk)
        # Cambiar el estado de aprobación
        overtime_entry.approved = not overtime_entry.approved
        overtime_entry.save()
        
        next_url = request.POST.get('next')
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        else:
            return redirect('overtime:overtime_list')
    return redirect('overtime:overtime_list')


@login_required
def edit_overtime(request, pk):
    overtime_entry = get_object_or_404(Overtime, pk=pk)
    if request.method == 'POST':
        form = OvertimeEditForm(request.POST, instance=overtime_entry)
        if form.is_valid():
            form.save()
            return redirect('overtime:overtime_list')
    return redirect('overtime:overtime_list')


@login_required
def delete_overtime(request, pk):
    overtime_entry = get_object_or_404(Overtime, pk=pk)
    if request.method == 'POST':
        overtime_entry.delete()
        return redirect('overtime:overtime_list')
    return redirect('overtime:overtime_list')


@login_required
def export_overtime_excel(request):

    today = date.today()
    if today.day < 24:
        start_date = (today - relativedelta(months=1)).replace(day=24)
        end_date = today.replace(day=24)
    else:
        start_date = today.replace(day=24)
        end_date = (today + relativedelta(months=1)).replace(day=24)

    overtime_entries = Overtime.objects.filter(fecha__gte=start_date, fecha__lt=end_date)

    person_name = request.GET.get('person_name', '')
    asset_name = request.GET.get('asset', '')
    date_filter = request.GET.get('date', '')

    if person_name:
        overtime_entries = overtime_entries.filter(nombre_completo__icontains=person_name)

    if asset_name:
        overtime_entries = overtime_entries.filter(asset__name__icontains=asset_name)

    if date_filter:
        overtime_entries = overtime_entries.filter(fecha=date_filter)

    overtime_entries = overtime_entries.order_by('fecha', 'asset', 'justificacion')
    wb = openpyxl.Workbook()
    ws = wb.active

    last_month = today - relativedelta(months=1)
    report_title = f"REPORTE 24 {last_month.strftime('%B')} hasta 24 {today.strftime('%B')} {today.year}"
    ws.append([report_title])
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=8)
    ws.cell(row=1, column=1).font = openpyxl.styles.Font(size=14, bold=True)

    headers = ['Nombre completo', 'Cédula', 'Fecha', 'Justificación', 'Hora inicio', 'Hora fin', 'Aprueba', 'Transporte']
    ws.append(headers)

    for col_num, column_title in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_num)
        cell.font = openpyxl.styles.Font(bold=True)
        ws.column_dimensions[get_column_letter(col_num)].width = 20  # Ajustar ancho de columna

    # Añadir los datos
    for entry in overtime_entries:
        # Calcular transporte
        if entry.hora_fin >= time(19, 0):  # 7:00 PM
            transporte = 'Sí'
        else:
            transporte = 'No'

        row = [
            entry.nombre_completo,
            entry.cedula,
            entry.fecha.strftime('%d/%m/%Y') if entry.fecha else '',
            entry.justificacion,
            entry.hora_inicio.strftime('%I:%M %p') if entry.hora_inicio else '',
            entry.hora_fin.strftime('%I:%M %p') if entry.hora_fin else '',
            'Sí' if entry.approved else 'No',
            transporte,
        ]
        ws.append(row)

    # Configurar la respuesta HTTP
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    filename = f"Reporte_Horas_Extras_{today.strftime('%Y%m%d')}.xlsx"
    response['Content-Disposition'] = f'attachment; filename={filename}'

    wb.save(response)
    return response


@login_required
def overtime_report(request):
    if request.method == 'POST':
        common_form = OvertimeCommonForm(request.POST)
        person_formset = OvertimePersonFormSet(request.POST)

        if common_form.is_valid() and person_formset.is_valid():

            try:
                asset = Asset.objects.get(supervisor=request.user)
            except Asset.DoesNotExist:
                asset = None 
                
            # Guardar los datos comunes
            fecha = common_form.cleaned_data['fecha']
            hora_inicio = common_form.cleaned_data['hora_inicio']
            hora_fin = common_form.cleaned_data['hora_fin']
            justificacion = common_form.cleaned_data['justificacion']

            # Iterar sobre el formset y crear un registro por persona
            for person_form in person_formset:
                nombre_completo = person_form.cleaned_data.get('nombre_completo')
                cedula = person_form.cleaned_data.get('cedula')
                cargo = person_form.cleaned_data.get('cargo')

                if not nombre_completo and not cargo:
                    continue

                Overtime.objects.create(
                    fecha=fecha,
                    hora_inicio=hora_inicio,
                    hora_fin=hora_fin,
                    justificacion=justificacion,
                    nombre_completo=nombre_completo,
                    cedula=cedula,
                    cargo=cargo,
                    reportado_por=request.user,
                    asset=asset,
                    approved=False 
                )

            return redirect('overtime:overtime_success')
    else:
        common_form = OvertimeCommonForm()
        person_formset = OvertimePersonFormSet()

    context = {
        'common_form': common_form,
        'person_formset': person_formset,
    }
    return render(request, 'overtime/overtime_report.html', context)


def overtime_success(request):
    return render(request, 'overtime/overtime_success.html')