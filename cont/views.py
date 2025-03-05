# con/views.py
from decimal import Decimal
from cont.models import Financiacion, AssetCost, GastosAdministrativos, CodigoContable
from openpyxl import load_workbook
from .forms import *
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from cont.forms import AssetCostUpdateForm
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.views.generic import ListView, DetailView


def cont_members_check(user):
    return user.is_superuser or user.groups.filter(name='cont_members').exists()


class FinanciacionCreateView(CreateView):
    model = Financiacion
    form_class = FinanciacionForm
    template_name = "cont/financiacion_form.html"
    
    def get_initial(self):
        initial = super().get_initial()
        asset_cost_pk = self.kwargs.get('asset_cost_pk')
        initial['asset_cost'] = asset_cost_pk
        return initial
    
    def form_valid(self, form):
        form.instance.asset_cost_id = self.kwargs.get('asset_cost_pk')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset_cost_pk = self.kwargs.get('asset_cost_pk')
        context['asset_cost_obj'] = AssetCost.objects.get(pk=asset_cost_pk)
        return context
    
    def get_success_url(self):
        return reverse_lazy('con:asset-detail', kwargs={'pk': self.kwargs.get('asset_cost_pk')})
    

class AssetCostListView(ListView):
    model = AssetCost
    template_name = "cont/asset_list.html"
    context_object_name = "asset_costs"

    def get_queryset(self):
        return AssetCost.objects.filter(asset__area__in=['a','c'], asset__show=True)


class AssetCostDetailView(DetailView):
    model = AssetCost
    template_name = "cont/asset_detail.html"
    context_object_name = "asset_cost"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ac = self.object
        # Cálculos de depreciación
        total_cost = (ac.initial_cost or Decimal('0')) + (ac.costo_adicional or Decimal('0'))
        depreciation = total_cost / Decimal('3600') if total_cost > 0 else Decimal('0')
        context['total_cost'] = total_cost
        context['depreciation'] = depreciation

        # Financiaciones
        financiaciones = ac.financiaciones.all()
        total_interest = sum((fin.monto * fin.tasa_interes / Decimal('12') * fin.plazo) for fin in financiaciones)
        total_interest_monthly = sum((fin.monto * fin.tasa_interes / Decimal('12')) for fin in financiaciones)
        context['financiaciones'] = financiaciones
        context['total_interest'] = total_interest
        context['total_interest_monthly'] = total_interest_monthly

        context['fp'] = ac.fp

        # Preparar pivot para GastosAdministrativos agrupados por el código exacto de la columna "cuenta"
        # pero solo para aquellos registros cuyo código (al inicio) coincida con alguno registrado en CodigoContable.
        from collections import defaultdict
        from .models import CodigoContable, GastosAdministrativos

        # Obtener todos los códigos contables registrados
        codigos_contables = list(CodigoContable.objects.all())
        # Crear un diccionario para agrupar: key = (codigo_contable, anio, mes)
        grouped = defaultdict(list)
        # Iterar sobre todos los registros de gastos administrativos
        gastos = GastosAdministrativos.objects.all()
        for gasto in gastos:
            # Para cada gasto, revisar si su campo 'codigo' (que es el valor exacto del excel) comienza con alguno de los códigos contables.
            for cc in codigos_contables:
                if gasto.codigo.startswith(cc.codigo):
                    key = (cc.codigo, gasto.anio, gasto.mes)
                    grouped[key].append(gasto)
                    break  # Solo se asocia a un código contable
        # Ahora, para la tabla pivot:
        # Queremos una fila por cada código contable (agrupando todos los registros de ese código, sin importar el mes)
        pivot_dict = defaultdict(lambda: {'codigo': None, 'descripcion': None, 'anio': None, 'total': Decimal('0'), 'detalles': [], 'meses': {}})
        for (cc_code, anio, mes), gastos_list in grouped.items():
            # Buscamos la descripción en CodigoContable
            descripcion = next((cc.nombre for cc in codigos_contables if cc.codigo == cc_code), "")
            # Para este grupo, sumamos el total (podríamos tomar el total del registro del mes mayor, pero aquí sumamos todos)
            total_group = sum(g.total for g in gastos_list)
            # En la fila de pivot, si ya existe para este código, actualizamos:
            if pivot_dict[cc_code]['codigo'] is None:
                pivot_dict[cc_code]['codigo'] = cc_code
                pivot_dict[cc_code]['descripcion'] = descripcion
                pivot_dict[cc_code]['anio'] = anio  # Suponemos que todos los registros para ese código tienen el mismo anio
                pivot_dict[cc_code]['total'] = total_group
                pivot_dict[cc_code]['detalles'].extend(gastos_list)
                pivot_dict[cc_code]['meses'][mes] = sum(g.promedio_mes for g in gastos_list)
            else:
                pivot_dict[cc_code]['total'] += total_group
                pivot_dict[cc_code]['detalles'].extend(gastos_list)
                if mes in pivot_dict[cc_code]['meses']:
                    pivot_dict[cc_code]['meses'][mes] += sum(g.promedio_mes for g in gastos_list)
                else:
                    pivot_dict[cc_code]['meses'][mes] = sum(g.promedio_mes for g in gastos_list)
        # Convertir a lista de pivot rows
        pivot_rows = list(pivot_dict.values())
        # Obtener la lista de meses únicos a mostrar (ordenada)
        unique_months = set()
        for row in pivot_rows:
            unique_months.update(row['meses'].keys())
        unique_months = sorted(unique_months)
        # Para cada pivot row, asegurarse de que haya una entrada para cada mes, aunque sea None
        for row in pivot_rows:
            for m in unique_months:
                row[m] = row['meses'].get(m)
        context['pivot_rows'] = pivot_rows
        context['unique_months'] = unique_months

        # Sumatorias generales si se desean
        context['total_gastos_sum'] = sum(g.total for g in gastos)
        context['total_promedio_sum'] = sum(g.promedio_mes for g in gastos)
        return context



@require_POST
def update_assetcost(request, pk):
    assetcost = get_object_or_404(AssetCost, pk=pk)
    form = AssetCostUpdateForm(request.POST, instance=assetcost)
    if form.is_valid():
        form.save()
        return JsonResponse({'success': True, 'initial_cost': str(assetcost.initial_cost)})
    else:
        return JsonResponse({'success': False, 'errors': form.errors})
    

@require_POST
def gastos_upload_ajax(request):
    form = GastosUploadForm(request.POST, request.FILES)
    if form.is_valid():
        excel_file = form.cleaned_data['excel_file']
        selected_mes = form.cleaned_data['mes']
        try:
            wb = load_workbook(filename=excel_file, data_only=True)
        except Exception as e:
            return JsonResponse({'success': False, 'error': 'Error al abrir el archivo.'})
        if 'query' not in wb.sheetnames:
            return JsonResponse({'success': False, 'error': 'La hoja "query" no existe en el archivo.'})
        ws = wb['query']
        
        # Asumimos que la primera fila contiene los encabezados
        headers = [cell.value for cell in ws[1]]
        header_map = {header: idx for idx, header in enumerate(headers)}
        required_columns = ['cuenta', 'nombrecuenta', 'fecha', 'Total']
        for col in required_columns:
            if col not in header_map:
                return JsonResponse({'success': False, 'error': f'La columna requerida "{col}" no se encontró.'})
        
        # Obtener códigos válidos desde CodigoContable
        codigos = CodigoContable.objects.all()
        valid_codes = {c.codigo: c.nombre for c in codigos}
        
        # Procesar registros: la clave de agrupación es (codigo_válido, anio, selected_mes, descripción_del_codigo)
        processed_groups = {}
        detailed_records = {}
        total_rows = 0
        matched_rows = 0
        
        for row in ws.iter_rows(min_row=2, values_only=True):
            total_rows += 1
            cuenta_val = row[header_map['cuenta']]
            if not cuenta_val:
                continue
            cuenta_str = str(cuenta_val).strip()
            matching_code = None
            # Se recorre la lista de códigos válidos para ver si el valor empieza con alguno
            for code in valid_codes.keys():
                if cuenta_str.startswith(code):
                    matching_code = code
                    break
            if matching_code:
                matched_rows += 1
                # Usar la descripción registrada en CodigoContable para el código válido
                descripcion_codigo = valid_codes[matching_code]
                fecha_val = row[header_map['fecha']]
                if isinstance(fecha_val, str):
                    try:
                        fecha_val = datetime.strptime(fecha_val, "%Y-%m-%d").date()
                    except Exception as e:
                        continue
                anio = fecha_val.year if fecha_val else None
                # Convertir el valor de "Total"
                total_val = row[header_map['Total']]
                try:
                    total_decimal = Decimal(str(total_val))
                except:
                    total_decimal = Decimal('0.00')
                # Clave de agrupación: basada en el código válido (no el valor completo de "cuenta")
                key = (matching_code, anio, selected_mes, descripcion_codigo)
                if key not in processed_groups:
                    processed_groups[key] = total_decimal
                    detailed_records[key] = []
                else:
                    processed_groups[key] += total_decimal
                # Guardar detalle para este registro
                detail = {
                    'cuenta': cuenta_str,
                    'nombre_cuenta': row[header_map['nombrecuenta']],
                    'fecha': fecha_val,
                    'total': total_decimal,
                    'mes': selected_mes
                }
                detailed_records[key].append(detail)
        
        created = 0
        updated = 0
        duplicate = 0
        for key, total_sum in processed_groups.items():
            codigo, anio, mes, descripcion = key
            qs = GastosAdministrativos.objects.filter(codigo=codigo, anio=anio, mes=mes)
            if qs.exists():
                duplicate += 1
                obj = qs.first()
                obj.total = total_sum  # Sobrescribe el total
                obj.save()
                updated += 1
            else:
                GastosAdministrativos.objects.create(
                    codigo=codigo,
                    descripcion=descripcion,
                    anio=anio,
                    mes=mes,
                    total=total_sum
                )
                created += 1
        
        message = (f"Archivo procesado correctamente: {created} registros creados, {updated} actualizados. "
                   f"Se leyeron {total_rows} filas, de las cuales {matched_rows} coincidieron con el criterio.")
        if duplicate:
            message += f" Se sobrescribieron {duplicate} registros existentes para el mes seleccionado."
        
        # Convertir las claves de detailed_records a cadena para que sean serializables en JSON
        detailed_records_serializable = {str(key): value for key, value in detailed_records.items()}
        
        return JsonResponse({
            'success': True, 
            'message': message,
            'details': detailed_records_serializable,
        })
    else:
        return JsonResponse({'success': False, 'errors': form.errors})