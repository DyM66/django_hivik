from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from dth.forms import UserProfileForm
from dth.models import UserProfile
from django.contrib.auth.models import User
from django.db import transaction
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
from .utils import *
import openpyxl
from openpyxl.utils import get_column_letter
from django.http import HttpResponse
from datetime import timedelta, datetime, time, date
import holidays
from django.contrib import messages
from datetime import time
import json
from got.models import Asset
from django.http import JsonResponse

# Horarios de trabajo
WEEKDAY_START = time(7, 30)
WEEKDAY_END = time(17, 0)

SATURDAY_START = time(8, 0)
SATURDAY_END = time(12, 0)

colombia_holidays = holidays.Colombia()

@login_required
def profile_update(request):
    user = request.user
    # Intenta obtener el perfil; si no existe, créalo
    profile, created = UserProfile.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile, user=user)
        if form.is_valid():
            # Actualizar datos del usuario
            user.first_name = form.cleaned_data.get('first_name')
            user.last_name = form.cleaned_data.get('last_name')
            user.email = form.cleaned_data.get('email')
            user.save()
            # Guardar perfil
            form.save()
            messages.success(request, 'Tu perfil ha sido actualizado exitosamente.')
            return redirect('got:asset-list')
        else:
            messages.error(request, 'Por favor corrige los errores indicados.')
    else:
        form = UserProfileForm(instance=profile, user=user, initial={
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
        })
    return render(request, 'dth/profile_update.html', {'form': form})


def hours_to_hhmm(total_hours):
    """Convierte total_hours (float) en un string 'X horas y Y minutos'."""
    hours = int(total_hours)
    minutes = int(round((total_hours - hours) * 60))
    return f"{hours}:{minutes}"

class OvertimeListView(LoginRequiredMixin, ListView):
    model = Overtime
    template_name = 'dth/overtime_list.html'
    paginate_by = 25

    def get_default_date_range(self):
        today = date.today()
        if today.day < 21:
            start_date = (today - relativedelta(months=1)).replace(day=21)
            end_date = today.replace(day=21)
        else:
            start_date = today.replace(day=21)
            end_date = (today + relativedelta(months=1)).replace(day=21)
        return start_date, end_date
    
    def parse_date_range(self):
        date_range_str = self.request.GET.get('date_range', '')
        if date_range_str:
            # Detecta separadores posibles
            if " to " in date_range_str:
                dates = date_range_str.split(" to ")
            elif " a " in date_range_str:
                dates = date_range_str.split(" a ")
            elif "," in date_range_str:
                dates = date_range_str.split(",")
            else:
                dates = []
            if len(dates) == 2:
                try:
                    start_date = datetime.strptime(dates[0].strip(), '%Y-%m-%d').date()
                    end_date = datetime.strptime(dates[1].strip(), '%Y-%m-%d').date()
                except ValueError:
                    start_date, end_date = self.get_default_date_range()
            else:
                try:
                    start_date = datetime.strptime(date_range_str.strip(), '%Y-%m-%d').date()
                    end_date = start_date + timedelta(days=1)
                except ValueError:
                    start_date, end_date = self.get_default_date_range()
        else:
            start_date, end_date = self.get_default_date_range()
        return start_date, end_date

    def get_queryset(self):
        start_date, end_date = self.parse_date_range()
        queryset = Overtime.objects.filter(fecha__gte=start_date, fecha__lt=end_date)

        # Filtros específicos
        person_name = self.request.GET.get('name', '').strip()
        cedula = self.request.GET.get('cedula', '').strip()
        asset_name = self.request.GET.get('asset', '').strip()
        aprobado_filter = self.request.GET.get('estado', 'all')

        if person_name:
            queryset = queryset.filter(nombre_completo__icontains=person_name)
        if cedula:
            queryset = queryset.filter(cedula__icontains=cedula)
        if asset_name:
            queryset = queryset.filter(asset__name__icontains=asset_name)
        if aprobado_filter == 'aprobado':
            queryset = queryset.filter(approved=True)
        elif aprobado_filter == 'no_aprobado':
            queryset = queryset.filter(approved=False)

        # Filtros por grupo de usuario
        current_user = self.request.user
        if current_user.groups.filter(name='mto_members').exists():
            pass  # Sin filtro adicional
        elif current_user.groups.filter(name='maq_members').exists():
            asset = Asset.objects.filter(models.Q(supervisor=current_user) | models.Q(capitan=current_user)).first()
            queryset = queryset.filter(asset=asset)
        elif current_user.groups.filter(name__in=['buzos_members', 'serport_members']).exists():
            queryset = queryset.none()

        return queryset.order_by('-fecha', 'asset', 'hora_inicio', 'justificacion')

    def get_total_hours(self, queryset):
        total_seconds = 0
        for entry in queryset:
            dt_start = datetime.combine(entry.fecha, entry.hora_inicio)
            dt_end = datetime.combine(entry.fecha, entry.hora_fin)
            diff = dt_end - dt_start
            total_seconds += diff.total_seconds()
        return round(total_seconds / 3600, 2)  # Total en horas

    def get_total_sunday_holiday_hours(self, queryset):
        total_seconds = 0
        for entry in queryset:
            dt_start = datetime.combine(entry.fecha, entry.hora_inicio)
            dt_end = datetime.combine(entry.fecha, entry.hora_fin)
            diff = dt_end - dt_start
            # Si la fecha es domingo o festiva, sumar la totalidad de la duración
            if entry.fecha.weekday() == 6 or entry.fecha in colombia_holidays:
                total_seconds += diff.total_seconds()
        return round(total_seconds / 3600, 2)

    # def get_total_nocturnal_hours(self, queryset):
    #     total_seconds = 0
    #     for entry in queryset:
    #         dt_start = datetime.combine(entry.fecha, entry.hora_inicio)
    #         dt_end = datetime.combine(entry.fecha, entry.hora_fin)
    #         if dt_end <= dt_start:
    #             dt_end += timedelta(days=1)
    #         overlap = get_nocturnal_overlap(dt_start, dt_end)
    #         total_seconds += overlap.total_seconds()
    #     return round(total_seconds / 3600, 2)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        start_date, end_date = self.parse_date_range()
        context['start_date'] = start_date.strftime('%Y-%m-%d')
        context['end_date'] = end_date.strftime('%Y-%m-%d')
        context['date_range'] = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        context['name'] = self.request.GET.get('name', '')
        context['cedula'] = self.request.GET.get('cedula', '')
        context['asset_filter'] = self.request.GET.get('asset', '')
        context['estado'] = self.request.GET.get('estado', 'all')
        
        total_hours = self.get_total_hours(queryset)
        context['total_hours'] = total_hours  # Valor numérico, por ejemplo 12.5
        context['total_hours_hhmm'] = hours_to_hhmm(total_hours)  # Formato HH:MM, por ejemplo "12:30"
        
        context['total_sunday_holiday_hours'] = hours_to_hhmm(self.get_total_sunday_holiday_hours(queryset))
        # context['total_nocturnal_hours'] = self.get_total_nocturnal_hours(queryset)
    
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
            date_asset_justification_groups.append({'fecha': fecha, 'assets': asset_groups})
        context['date_asset_groups'] = date_asset_justification_groups
        # También enviamos la lista de activos para el select (assets de área 'a')
        context['assets'] = Asset.objects.filter(area='a', show=True).order_by('name')
        context['holiday_dates'] = json.dumps([d.strftime('%Y-%m-%d') for d in colombia_holidays.keys()])
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
            return redirect('dth:overtime_list')
    return redirect('dth:overtime_list')


@login_required
def edit_overtime(request, pk):
    overtime_entry = get_object_or_404(Overtime, pk=pk)
    if request.method == 'POST':
        form = OvertimeEditForm(request.POST, instance=overtime_entry)
        if form.is_valid():
            form.save()
            return redirect('dth:overtime_list')
    return redirect('dth:overtime_list')


@login_required
def delete_overtime(request, pk):
    overtime_entry = get_object_or_404(Overtime, pk=pk)
    if request.method == 'POST':
        overtime_entry.delete()
        return redirect('dth:overtime_list')
    return redirect('dth:overtime_list')


def get_default_date_range():
    today = date.today()
    if today.day < 21:
        start_date = (today - relativedelta(months=1)).replace(day=21)
        end_date = today.replace(day=21)
    else:
        start_date = today.replace(day=21)
        end_date = (today + relativedelta(months=1)).replace(day=21)
    return start_date, end_date

def parse_date_range(request):
    date_range_str = request.GET.get('date_range', '')
    if date_range_str:
        # Detecta separadores posibles
        if " to " in date_range_str:
            dates = date_range_str.split(" to ")
        elif " a " in date_range_str:
            dates = date_range_str.split(" a ")
        elif "," in date_range_str:
            dates = date_range_str.split(",")
        else:
            dates = []
        if len(dates) == 2:
            try:
                start_date = datetime.strptime(dates[0].strip(), '%Y-%m-%d').date()
                end_date = datetime.strptime(dates[1].strip(), '%Y-%m-%d').date()
            except ValueError:
                start_date, end_date = get_default_date_range()
        else:
            try:
                start_date = datetime.strptime(date_range_str.strip(), '%Y-%m-%d').date()
                end_date = start_date + timedelta(days=1)
            except ValueError:
                start_date, end_date = get_default_date_range()
    else:
        start_date, end_date = get_default_date_range()
    return start_date, end_date

def filter_overtime_queryset(request):
    # Rango de fechas
    start_date, end_date = parse_date_range(request)
    qs = Overtime.objects.filter(fecha__gte=start_date, fecha__lt=end_date)

    # Filtros por nombre, cédula y asset
    person_name = request.GET.get('name', '').strip()
    cedula = request.GET.get('cedula', '').strip()
    asset_name = request.GET.get('asset', '').strip()
    estado = request.GET.get('estado', 'all')

    if person_name:
        qs = qs.filter(nombre_completo__icontains=person_name)
    if cedula:
        qs = qs.filter(cedula__icontains=cedula)
    if asset_name:
        qs = qs.filter(asset__name__icontains=asset_name)
    if estado == 'approved':
        qs = qs.filter(approved=True)
    elif estado == 'no_aprobado':
        qs = qs.filter(approved=False)

    # Filtros según grupo de usuario
    current_user = request.user
    if current_user.groups.filter(name='mto_members').exists():
        pass  # Sin filtro adicional
    elif current_user.groups.filter(name='maq_members').exists():
        asset = Asset.objects.filter(models.Q(supervisor=current_user) | models.Q(capitan=current_user)).first()
        qs = qs.filter(asset=asset)
    elif current_user.groups.filter(name__in=['buzos_members', 'serport_members']).exists():
        qs = qs.none()

    return qs.order_by('-fecha', 'asset', 'hora_inicio', 'justificacion')

@login_required
def export_overtime_excel(request):
    qs = filter_overtime_queryset(request)

    wb = openpyxl.Workbook()
    ws = wb.active

    today = date.today()
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
        ws.column_dimensions[get_column_letter(col_num)].width = 20

    # Añadir los datos
    for entry in qs:
        # Calcular transporte (puedes ajustar esta lógica según lo necesites)
        transporte = 'Sí' if entry.hora_fin >= time(19, 0) else 'No'

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
                asset = Asset.objects.filter(models.Q(supervisor=request.user) | models.Q(capitan=request.user)).first()
            except Asset.DoesNotExist:
                asset = None 
                
            # Guardar los datos comunes
            fecha = common_form.cleaned_data['fecha']
            hora_inicio = common_form.cleaned_data['hora_inicio']
            hora_fin = common_form.cleaned_data['hora_fin']
            justificacion = common_form.cleaned_data['justificacion']
            overtime_periods = calcular_horas_extras(fecha, hora_inicio, hora_fin)

            if not overtime_periods:
                messages.warning(request, 'Las horas reportadas no califican como horas extras.')
                return redirect('overtime:overtime_report')
            
            def subtract_time_ranges(desired_start, desired_end, existing_ranges):
                intervals = [(desired_start, desired_end)]
                for ex_start, ex_end in existing_ranges:
                    new_intervals = []
                    for interval_start, interval_end in intervals:
                        # No hay solapamiento
                        if ex_end <= interval_start or ex_start >= interval_end:
                            new_intervals.append((interval_start, interval_end))
                        else:
                            # Hay solapamiento, ajustamos los intervalos
                            if ex_start > interval_start:
                                new_intervals.append((interval_start, ex_start))
                            if ex_end < interval_end:
                                new_intervals.append((ex_end, interval_end))
                    intervals = new_intervals
                return intervals

            for person_form in person_formset:
                nombre_completo = person_form.cleaned_data.get('nombre_completo')
                cedula = person_form.cleaned_data.get('cedula')
                cargo = person_form.cleaned_data.get('cargo')

                if not nombre_completo and not cargo:
                    continue

                # Obtener los registros existentes para la cédula y fecha
                existing_entries = Overtime.objects.filter(
                    cedula=cedula,
                    fecha=fecha,
                ).order_by('hora_inicio')

                existing_ranges = [(entry.hora_inicio, entry.hora_fin) for entry in existing_entries]

                created_any = False  # Para verificar si se creó al menos un registro

                for period_start, period_end in overtime_periods:
                    # Restar los intervalos existentes
                    non_overlapping_intervals = subtract_time_ranges(period_start, period_end, existing_ranges)
                    if not non_overlapping_intervals:
                        messages.warning(request, f'Todas las horas reportadas para {nombre_completo} ({cedula}) en el periodo {period_start.strftime("%I:%M %p")} - {period_end.strftime("%I:%M %p")} ya han sido registradas.')
                        continue
                    for interval_start, interval_end in non_overlapping_intervals:
                        Overtime.objects.create(
                            fecha=fecha,
                            hora_inicio=interval_start,
                            hora_fin=interval_end,
                            justificacion=justificacion,
                            nombre_completo=nombre_completo,
                            cedula=cedula,
                            cargo=cargo,
                            reportado_por=request.user,
                            asset=asset,
                            approved=False 
                        )
                        # Añadir el nuevo intervalo a la lista de existentes
                        existing_ranges.append((interval_start, interval_end))
                        existing_ranges.sort(key=lambda x: x[0])  # Ordenar por hora de inicio
                        created_any = True
                    if len(non_overlapping_intervals) < len(overtime_periods):
                        messages.warning(request, f'Algunas horas reportadas para {nombre_completo} ({cedula}) en el periodo {period_start.strftime("%I:%M %p")} - {period_end.strftime("%I:%M %p")} ya han sido registradas y fueron excluidas.')
                if created_any:
                    messages.success(request, f'Reporte de horas extras para {nombre_completo} ({cedula}) ha sido registrado.')
                else:
                    messages.warning(request, f'No se pudo registrar ninguna hora extra para {nombre_completo} ({cedula}).')

            return redirect('dth:overtime_success')
    else:
        common_form = OvertimeCommonForm()
        person_formset = OvertimePersonFormSet()

    current_year = date.today().year
    next_year = current_year + 1
    colombia_holidays = holidays.Colombia(years=[current_year, next_year])
    # Obtener las fechas en formato 'YYYY-MM-DD'
    holiday_dates = [h.strftime('%Y-%m-%d') for h in colombia_holidays.keys()]

    context = {
        'common_form': common_form,
        'person_formset': person_formset,
        'holiday_dates': json.dumps(holiday_dates),
    }
    return render(request, 'dth/overtime_report.html', context)


def overtime_success(request):
    return render(request, 'dth/overtime_success.html')


def calcular_horas_extras(fecha, hora_inicio, hora_fin):
    overtime_periods = []
    day_type = None  # 'weekday', 'saturday', 'sunday', 'holiday'

    if fecha in colombia_holidays:
        day_type = 'holiday'
    elif fecha.weekday() == 6:  # Domingo
        day_type = 'sunday'
    elif fecha.weekday() == 5:  # Sábado
        day_type = 'saturday'
    else:
        day_type = 'weekday'

    # Definir el horario laboral según el tipo de día
    if day_type == 'weekday':
        start_work = WEEKDAY_START
        end_work = WEEKDAY_END
    elif day_type == 'saturday':
        start_work = SATURDAY_START
        end_work = SATURDAY_END
    else:
        # Domingos y festivos: todo es horas extras
        if hora_inicio < hora_fin:
            overtime_periods.append((hora_inicio, hora_fin))
        return overtime_periods

    # Horas antes del inicio de la jornada laboral
    if hora_inicio < start_work:
        overtime_periods.append((hora_inicio, min(hora_fin, start_work)))

    # Horas después del fin de la jornada laboral
    if hora_fin > end_work:
        overtime_periods.append((max(hora_inicio, end_work), hora_fin))

    # Horas completamente fuera del horario laboral
    if hora_inicio >= hora_fin:
        return overtime_periods

    if hora_inicio >= end_work or hora_fin <= start_work:
        overtime_periods.append((hora_inicio, hora_fin))

    return overtime_periods


def gerencia_nomina_view(request):
    """
    Vista exclusiva para la gerencia (Jennifer Padilla).
    Permite subir un Excel y procesar la creación/actualización de NominaReport.
    """
    template_name = "dth/gerencia_nomina.html"

    if request.method == "POST":
        form = UploadNominaReportForm(request.POST, request.FILES)
        if form.is_valid():
            # Se extrae el archivo excel
            excel_file = request.FILES['excel_file']

            # Deshabilitar el botón y mostrar mensaje de "procesando..."
            # -> Esto se maneja desde el template con JavaScript, ver ejemplo abajo.

            # Lógica para procesar el archivo
            try:
                # Abrimos el workbook con openpyxl
                wb = openpyxl.load_workbook(excel_file, data_only=True)
                # Asumimos que solo hay UNA hoja
                sheet = wb.active

                # Mapeo de codigos -> nombre de campo en NominaReport
                # Clave = el prefijo con el que inicia la celda de "Concepto"
                CODE_FIELD_MAP = {
                    'DV01': 'dv01',
                    'DV23': 'dv25',
                    'DV03': 'dv03',
                    'DV103': 'dv103',
                    'DV27': 'dv27',
                    'DV30': 'dv30',
                    'DX03': 'dx03',
                    'DX05': 'dx05',
                    'DX01': 'dx01',
                    'DX07': 'dx07',
                    'DX12': 'dx12',
                    'DX63': 'dx63',
                    'DX64': 'dx64',
                    'DX66': 'dx66',
                    # Ejemplo: si tienes más códigos, agrégalos aquí.
                    # 'DV48': 'dv48', etc.
                }

                rows_created = 0
                rows_updated = 0

                # Buscar el índice de columna (asumiendo encabezados en la primera fila)
                # Para evitar problemas con la posición exacta, lo hacemos flexible:
                headers = {cell.value: idx for idx, cell in enumerate(sheet[1], start=1)}
                print("DEBUG - Headers leídos:", headers)

                # Revisar que existan las columnas mínimas
                required_cols = [
                    "Empleado", "FechaMovimiento", "Concepto",
                    "ValorDevengo", "ValorDeduccion"
                ]
                clean_headers = {str(k).strip(): v for k, v in headers.items() if k is not None}

                for col in required_cols:
                    if col not in clean_headers:
                        messages.error(request, f"Falta la columna requerida '{col}' en el Excel.")
                        return render(request, template_name, {"form": form})

                # Iterar sobre las filas (omitir la primera, que es encabezado)
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    # Tomar valores de la fila según las columnas
                    empleado = row[headers["Empleado"] - 1]          # doc_number
                    fecha_mov = row[headers["FechaMovimiento"] - 1]  # string con fecha

                    fecha_celda = row[headers["FechaMovimiento"] - 1]
                    if isinstance(fecha_celda, datetime):
                        # Es un objeto datetime => tomar su fecha
                        parsed_date = fecha_celda.date()
                        mes = parsed_date.month
                        anio = parsed_date.year
                    elif isinstance(fecha_celda, date):
                        # A veces openpyxl puede devolver date directamente (sin tiempo)
                        mes = fecha_celda.month
                        anio = fecha_celda.year
                    elif isinstance(fecha_celda, str):
                        # Intentar parsear como "d/m/yyyy"
                        # Ojo con más validaciones según tu archivo
                        try:
                            parsed_date = datetime.strptime(fecha_celda.strip(), "%d/%m/%Y")
                            mes = parsed_date.month
                            anio = parsed_date.year
                        except ValueError:
                            # Manejar formato inválido
                            continue
                    else:
                        # No es ninguno de los tipos esperados => se ignora
                        continue

                    concepto_original = row[clean_headers["Concepto"] - 1] or ""
                    concepto_upper = str(concepto_original).strip().upper()

                    print("DEBUG - Concepto leido:", concepto_original) 

                    # Settear found_field en None
                    found_field = None
                    for code_prefix, field_name in CODE_FIELD_MAP.items():
                        # Buscamos si concepto_upper arranca con code_prefix
                        if concepto_upper.startswith(code_prefix):
                            found_field = field_name
                            break

                    if found_field:
                        print("DEBUG - matched", found_field, "para concepto", concepto_upper)
                    else:
                        print("DEBUG - sin match para", concepto_upper)

                    valor_devengo = row[headers["ValorDevengo"] - 1] or 0
                    valor_deduccion = row[headers["ValorDeduccion"] - 1] or 0

                    # Verificamos si hay doc_number en Nomina
                    if empleado is None:
                        continue  # Ignorar filas vacías
                    try:
                        nomina_obj = Nomina.objects.get(doc_number=str(empleado))
                    except Nomina.DoesNotExist:
                        # Si no existe en Nomina, puedes decidir crearlo o ignorarlo
                        # Aquí optamos por ignorar y continuar
                        continue

                    # Extraer mes y año de 'FechaMovimiento' (ej: "1/02/2025")
                    # Asumiendo formato: d/m/yyyy
                    # try:
                    #     parsed_date = datetime.strptime(str(fecha_mov), "%d/%m/%Y")
                    #     mes = parsed_date.month
                    #     anio = parsed_date.year
                    # except ValueError:
                    #     # Si no logra parsear, omitir
                    #     continue

                    # Verificar si ya existe un NominaReport con esa Nomina y mes/año
                    with transaction.atomic():
                        nomina_report, created = NominaReport.objects.get_or_create(
                            nomina=nomina_obj,
                            mes=mes,
                            anio=anio
                        )
                        if created:
                            rows_created += 1
                        else:
                            rows_updated += 1

                        # Detectar si el Concepto inicia con algún código
                        # p.ej. "DV01 SUELDO BASICO" -> arranca con "DV01"
                        found_field = None
                        concepto_upper = concepto_upper.strip().upper()
                        for code_prefix, field_name in CODE_FIELD_MAP.items():
                            if concepto_upper.startswith(code_prefix):
                                found_field = field_name
                                break

                        # Tomar el valor "no cero" entre ValorDevengo y ValorDeduccion
                        # Si ambos son 0, no hacemos nada
                        valor = Decimal('0')
                        if valor_devengo not in [None, 0]:
                            valor = Decimal(valor_devengo)
                        elif valor_deduccion not in [None, 0]:
                            valor = Decimal(valor_deduccion)

                        if found_field and valor != 0:
                            # Asignar dinámicamente al campo correspondiente
                            setattr(nomina_report, found_field, valor)
                            nomina_report.save()

                # Al terminar
                messages.success(
                    request,
                    (f"Proceso finalizado. Se crearon {rows_created} registros nuevos "
                     f"y se actualizaron {rows_updated} registros existentes.")
                )
                return redirect('dth:gerencia_nomina')  # o simplemente recargar
            except Exception as e:
                messages.error(request, f"Ocurrió un error procesando el archivo: {str(e)}")
    else:
        form = UploadNominaReportForm()

    # ==== CONSULTAMOS LOS REGISTROS PARA LA TABLA ====
    # Recuperamos todos los NominaReport, con su Nomina relacionada
    # Orden: primero por el nombre del empleado, luego mes y año.
    # Nota: Para “nombre completo”, un truco es concatenar en un campo simulado
    #       o podemos sólo ordenar por “nomina__name” y “nomina__surname”.
    reports = (NominaReport.objects
               .select_related('nomina')
               .order_by('nomina__name', 'nomina__surname', 'mes', 'anio'))

    # Aquí hacemos los cálculos necesarios claramente:
    processed_reports = []
    for nr in reports:
        salario = nr.nomina.salary or 0
        dv01 = nr.dv01 or 0
        dv25 = nr.dv25 or 0
        dias_sueldo_basico = round((dv01 / (salario / 30)), 2) if salario else 0
        dias_vacaciones = round((dv25 / (salario / 30)), 2) if salario else 0

        processed_reports.append({
            'report': nr,
            'dias_sueldo_basico': dias_sueldo_basico,
            'dias_vacaciones': dias_vacaciones,
            # Aquí puedes añadir otros cálculos que necesites
        })

    nomina_qs = Nomina.objects.all().order_by('name', 'surname')

    context = {
        "form": form,
        "processed_reports": processed_reports,
        'nomina_list': nomina_qs
    }

    return render(request, template_name, context)


# dth/views.py (continuación)

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side, NamedStyle
from decimal import Decimal
from django.http import HttpResponse

@login_required
def export_gerencia_nomina_excel(request):
    """
    Exporta la tabla de NominaReport a un archivo Excel con estilos y formatos 
    similares a la tabla de la vista de Nómina Gerencia.
    """
    # 1) Obtención de registros
    reports = (NominaReport.objects
               .select_related('nomina')
               .order_by('nomina__name', 'nomina__surname', 'mes', 'anio'))
    
    # 2) Crear workbook y hoja
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Nómina Gerencia"
    
    # 3) Definir encabezados y configurar estilos
    headers = [
        "Cédula del empleado", "Nombre del Empleado", "Cargo", "MES", "AÑO", "Salario",
        "# días sueldo básico", "Sueldo Básico (dv01)", "# días vacaciones", "Pago Vacaciones (dv25)",
        "Subsidio transporte (dv03)", "Licencia familia (dv103)", "Provisión vacaciones",
        "DV27 Intereses Ces. Ant", "Prima de Servicio", "Cesantías (dv30)",
        "Intereses de Cesantías", "Salud colab.", "Pensión colab (dx03)",
        "Fdo. solidar. (dx05)", "Pensión empleador", "ARL empleador",
        "Caja comp.", "Ret. Fuente", "Exequias Lordoy (dx07)",
        "Desc. pensión voluntaria (dx12)", "Banco Occidente (dx63)",
        "Confenalco (dx64)", "Préstamo (dx66)", "Neto a pagar"
    ]
    
    # Estilo para encabezados
    header_font = Font(bold=True, color="000000")
    header_fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    thin_side = Side(border_style="thin", color="000000")
    header_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
    
    # Escribir encabezados y ajustar anchos
    for col_num, col_name in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_num, value=col_name)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = header_border
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_num)].width = 20

    # Número de columna de cada campo de moneda (según índice en la lista de encabezados)
    currency_columns = [6, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
                        21, 22, 23, 24, 25, 26, 27, 28, 29, 30]
    currency_format = '"COP " #,##0.00'

    # 4) Agregar filas de datos
    row_index = 2
    for nr in reports:
        emp = nr.nomina
        # Calcular # días sueldo básico y # días vacaciones
        dias_sb = Decimal('0.00')
        dias_vac = Decimal('0.00')
        if emp.salary and nr.dv01:
            dias_sb = nr.dv01 / (Decimal(emp.salary) / Decimal('30'))
        if emp.salary and nr.dv25:
            dias_vac = nr.dv25 / (Decimal(emp.salary) / Decimal('30'))
        
        data_row = [
            emp.doc_number,
            f"{emp.name} {emp.surname}",
            emp.position,
            nr.mes,
            nr.anio,
            float(emp.salary or 0),
            float(dias_sb),
            float(nr.dv01 or 0),
            float(dias_vac),
            float(nr.dv25 or 0),
            float(nr.dv03 or 0),
            float(nr.dv103 or 0),
            float(nr.provision_vacaciones or 0),  # dv25 * 4.17%
            float(nr.dv27 or 0),
            float(nr.prima_servicio or 0),       # (dv01 + dv25 + dv03)*0.0833
            float(nr.dv30 or 0),
            float(nr.intereses_cesantias or 0),  # dv30 * 0.01
            float(nr.salud_aporte or 0),         # (dv01 + dv25) * 0.04
            float(nr.dx03 or 0),
            float(nr.dx05 or 0),
            float(nr.pension_aporte_empleador or 0),
            float(nr.arl_aporte or 0),
            float(nr.caja_compensacion_aporte or 0),
            float(nr.dx01 or 0),
            float(nr.dx07 or 0),
            float(nr.dx12 or 0),
            float(nr.dx63 or 0),
            float(nr.dx64 or 0),
            float(nr.dx66 or 0),
            float(nr.neto_a_pagar or 0),
        ]
        # Escribir la fila en la hoja
        for col_num, value in enumerate(data_row, start=1):
            cell = ws.cell(row=row_index, column=col_num, value=value)
            cell.border = header_border
            # Alinear a la derecha para números (excepto cédula y texto)
            if col_num in currency_columns or col_num in [7, 9]:
                cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
            # Si es columna de moneda, aplica el formato
            if col_num in currency_columns:
                cell.number_format = currency_format
        row_index += 1

    # 5) Retornar el archivo Excel como respuesta
    filename = "NominaGerencia.xlsx"
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response

@login_required
def nomina_edit(request, pk):
    """
    Vista que edita o elimina un registro de Nomina.

    - Si POST incluye 'action=delete', se elimina el registro.
      -> Si es AJAX, se responde con JSON.
      -> Si no es AJAX, se redirige con un mensaje.
    - Si no incluye 'action=delete', se asume edición de campos.
    """
    nomina_obj = get_object_or_404(Nomina, pk=pk)

    if request.method == 'POST':
        # Verificamos si es petición de borrado (action=delete)
        action = request.POST.get('action')
        if action == 'delete':
            nomina_obj.delete()

            # Si es AJAX, devolvemos JSON para que JS manipule la tabla sin recargar
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'deleted': True})

            # No es AJAX => redirigimos con mensaje
            messages.success(request, "Empleado eliminado con éxito.")
            return redirect('dth:gerencia_nomina')

        # De lo contrario, es edición
        form = NominaForm(request.POST, instance=nomina_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Registro de nómina actualizado.")
            return redirect('dth:gerencia_nomina')
        else:
            messages.error(request, "Por favor revisa los campos del formulario.")
    else:
        # GET => mostrar el formulario (opcional si deseas cargar un template)
        form = NominaForm(instance=nomina_obj)

    # Podrías renderizar un template si deseas un formulario de edición fuera del modal
    return render(request, 'dth/nomina_form.html', {'form': form, 'object': nomina_obj})


# dth/views.py (complemento)
@login_required
def nomina_create(request):
    """
    Crea un nuevo registro de Nomina.
    """
    if request.method == 'POST':
        form = NominaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Empleado creado con éxito.')
            return redirect('dth:gerencia_nomina') # O la misma página modal
        else:
            messages.error(request, 'Hay errores en el formulario.')
    else:
        form = NominaForm()

    return render(request, 'dth/nomina_form.html', {'form': form})
