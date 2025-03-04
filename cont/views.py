# con/views.py
from decimal import Decimal
from cont.models import AssetCost
from openpyxl import load_workbook
from .forms import *
from datetime import datetime


def cont_members_check(user):
    return user.is_superuser or user.groups.filter(name='cont_members').exists()


# con/views.py
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.views.generic import ListView, DetailView
from .models import Financiacion, AssetCost, GastosAdministrativos

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
        total_cost = (ac.initial_cost or Decimal('0')) + (ac.costo_adicional or Decimal('0'))
        depreciation = total_cost / Decimal('43800') if total_cost > 0 else Decimal('0')
        context['total_cost'] = total_cost
        context['depreciation'] = depreciation

        financiaciones = ac.financiaciones.all()
        total_interest = sum(
            (fin.monto * fin.tasa_interes / Decimal('12') * fin.plazo) for fin in financiaciones
        )
        # Calculamos el total de intereses mensuales (la suma de la cuota mensual)
        total_interest_monthly = sum(
            (fin.monto * fin.tasa_interes / Decimal('12')) for fin in financiaciones
        )
        context['financiaciones'] = financiaciones
        context['total_interest'] = total_interest
        context['total_interest_monthly'] = total_interest_monthly
          
        context['cont_a_los_gastos'] = ac.cont_a_los_gastos
        context['fp'] = ac.fp

        # Agregamos todos los registros de GastosAdministrativos
        gastos = GastosAdministrativos.objects.all()
        context['gastos'] = gastos
        context['total_gastos_sum'] = sum(g.total for g in gastos)
        context['total_promedio_sum'] = sum(g.promedio_mes for g in gastos)
        return context


# con/views.py (agregar al final del archivo)
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from cont.forms import AssetCostUpdateForm

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
        required_columns = ['mayor', 'Nombre Mayor', 'fecha', 'Total']
        for col in required_columns:
            if col not in header_map:
                return JsonResponse({'success': False, 'error': f'La columna requerida "{col}" no se encontró.'})
        codes = {"5105", "5110", "5115", "5120", "5125", "5135", "5140", "5145", "5150", "5155", "5195", "5305", "5315", "5395"}
        processed_codes = {}
        total_rows = 0
        matched_rows = 0
        for row in ws.iter_rows(min_row=2, values_only=True):
            total_rows += 1
            mayor_val = row[header_map['mayor']]
            if mayor_val is None:
                continue
            mayor_str = str(mayor_val).strip()
            if mayor_str in codes:
                matched_rows += 1
                codigo = mayor_str
                descripcion = row[header_map['Nombre Mayor']]
                fecha_val = row[header_map['fecha']]
                if isinstance(fecha_val, str):
                    try:
                        fecha_val = datetime.strptime(fecha_val, "%Y-%m-%d").date()
                    except Exception as e:
                        continue
                anio = fecha_val.year if fecha_val else None
                total_val = row[header_map['Total']]
                try:
                    total_decimal = Decimal(str(total_val))
                except:
                    total_decimal = Decimal('0.00')
                key = (codigo, anio, descripcion)
                processed_codes[key] = processed_codes.get(key, Decimal('0.00')) + total_decimal
        created = 0
        updated = 0
        for (codigo, anio, descripcion), total_sum in processed_codes.items():
            obj, created_flag = GastosAdministrativos.objects.get_or_create(
                codigo=codigo,
                anio=anio,
                defaults={'descripcion': descripcion, 'total': total_sum}
            )
            if not created_flag:
                obj.total += total_sum
                obj.save()
                updated += 1
            else:
                created += 1
        return JsonResponse({
            'success': True, 
            'message': f"Archivo procesado correctamente: {created} registros creados, {updated} actualizados. "
                       f"Se leyeron {total_rows} filas, de las cuales {matched_rows} coincidieron con el criterio.",
        })
    else:
        return JsonResponse({'success': False, 'errors': form.errors})