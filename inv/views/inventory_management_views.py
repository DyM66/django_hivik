import re
from datetime import datetime, date
from decimal import Decimal
from itertools import groupby
from operator import attrgetter

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Sum, Max
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, permission_required

from got.models import Asset, Item
from got.utils import generate_excel, render_to_pdf
from ope.models import Operation
from inv.models import Transaction
from inv.models.inventory import Suministro
from inv.utils.supplies_utils import get_suministros, handle_inventory_update, handle_transfer, handle_delete_transaction


@login_required
@permission_required('inv.can_add_supply', raise_exception=True)
def create_supply_view(request, abbreviation):
    """
    Vista separada para crear un suministro (Supply) asociado a un activo (Asset).
    Retorna JSON, pero utiliza también django.contrib.messages para mostrar el resultado.
    """
    if request.method != 'POST':
        # Podrías manejarlo de distintas maneras, aquí retornamos un JSON de error
        return JsonResponse({
            'success': False,
            'message': 'Método inválido. Use POST para crear un suministro.'
        }, status=405)

    # 1) Verificar si se recibió el item_id
    item_id = request.POST.get('item_id')
    if not item_id:
        messages.error(request, 'No se ha proporcionado un artículo válido.')
        return JsonResponse({'success': False, 'message': 'item_id requerido.'}, status=400)

    # 2) Buscar el Asset
    asset = get_object_or_404(Asset, abbreviation=abbreviation)

    # 3) Intentar obtener el Item
    try:
        item = Item.objects.get(pk=item_id)
    except Item.DoesNotExist:
        messages.error(request, 'El artículo seleccionado no existe.')
        return JsonResponse({'success': False, 'message': 'El artículo no existe.'}, status=404)

    # 4) Evitar duplicados (un item no puede repetirse para el mismo asset)
    if Suministro.objects.filter(asset=asset, item=item).exists():
        msg_error = f'El suministro para "{item.name}" ya existe en este activo.'
        messages.error(request, msg_error)
        return JsonResponse({'success': False, 'message': msg_error}, status=400)

    # 5) Crear el suministro
    Suministro.objects.create(item=item, cantidad=Decimal('0.00'), asset=asset)

    # 6) Agregar un mensaje de éxito
    msg_success = f'Suministro "{item.name}" creado exitosamente en {asset.name}.'
    messages.success(request, msg_success)

    return JsonResponse({'success': True, 'message': msg_success})


class AssetInventoryBaseView(LoginRequiredMixin, View):
    template_name = 'inventory_management/asset_inventory_report.html'
    keyword_filter = None
    keyword_filter2 = None

    def get(self, request, abbreviation):
        asset = get_object_or_404(Asset, abbreviation=abbreviation)
        suministros = get_suministros(asset, self.keyword_filter)

        transacciones_historial = self.get_transacciones_historial(asset)
        ultima_fecha_transaccion = transacciones_historial.aggregate(Max('fecha'))['fecha__max'] or "---"
        context = self.get_context_data(request, asset, suministros, transacciones_historial, ultima_fecha_transaccion)
        return render(request, self.template_name, context)

    def post(self, request, abbreviation):
        asset = get_object_or_404(Asset, abbreviation=abbreviation)
        suministros = get_suministros(asset, self.keyword_filter)
        action = request.POST.get('action', '')

        if action == 'download_excel':
            headers_mapping = self.get_headers_mapping()
            filename = self.get_filename()
            transacciones_historial = self.get_transacciones_historial(asset)
            return generate_excel(transacciones_historial, headers_mapping, filename)

        elif action == 'transfer_supply':
            suministro_id = request.POST.get('transfer_suministro_id')
            suministro = get_object_or_404(Suministro, id=suministro_id, asset=asset)
            transfer_fecha_str = request.POST.get('transfer_fecha', '')

            if not re.match(r'^\d{4}-\d{2}-\d{2}$', transfer_fecha_str):
                messages.error(request, "Fecha inválida de transferencia: usa el formato YYYY-MM-DD.")
                return self.redirect_with_next(request)
            
            result = handle_transfer(
                request,
                asset,
                suministro,
                request.POST.get('transfer_cantidad', '0') or '0',
                request.POST.get('destination_asset_id'),
                request.POST.get('transfer_motivo', ''),
                transfer_fecha_str 
            )
            if isinstance(result, HttpResponse):
                return result
            else:
                return self.redirect_with_next(request)

        elif action == 'update_inventory':
            motivo_global = ''
            fecha_reporte_str = request.POST.get('fecha_reporte', timezone.now().date().strftime('%Y-%m-%d'))

            # 1) Verificar si coincide con el patrón YYYY-MM-DD
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', fecha_reporte_str):
                messages.error(request, "Fecha inválida: usa el formato YYYY-MM-DD.")
                return self.redirect_with_next(request)
            
            try:
                fecha_reporte = datetime.strptime(fecha_reporte_str, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, "Fecha inválida: no se pudo interpretar el valor ingresado.")
                return self.redirect_with_next(request)

            # 3) Comparar con la fecha actual
            if fecha_reporte > timezone.now().date():
                messages.error(request, 'La fecha del reporte no puede ser mayor a la fecha actual.')
                return self.redirect_with_next(request)

            operation = Operation.objects.filter(asset=asset, confirmado=True, start__lte=fecha_reporte, end__gte=fecha_reporte).first()
            if operation:
                motivo_global = operation.proyecto

            result = handle_inventory_update(request, asset, suministros, motivo_global)
            if isinstance(result, HttpResponse):
                return result
            else:
                return self.redirect_with_next(request)

        else:
            messages.error(request, 'Acción no reconocida.')
            return self.redirect_with_next(request)

    def get_context_data(self, request, asset, suministros, transacciones_historial, ultima_fecha_transaccion):
        motonaves = Asset.objects.filter(show=True)
        available_items = Item.objects.exclude(id__in=suministros.values_list('item_id', flat=True))
        users = set(transacciones_historial.values_list('user', flat=True))
        users_unicos = list(users)
        secciones_dict = dict(Item.SECCION) 
        context = {
            'asset': asset,
            'suministros': suministros,
            'ultima_fecha_transaccion': ultima_fecha_transaccion,
            'transacciones_historial': transacciones_historial,
            'fecha_actual': timezone.now().date(),
            'motonaves': motonaves,
            'available_items': available_items,
            'articulos_unicos': self.get_articulos_unicos(transacciones_historial),
            'users_unicos': users_unicos,
            'secciones_dict': secciones_dict
        }
        return context
    
    def get_articulos_unicos(self, transacciones_historial):
        items_en_historial = set()
        for t in transacciones_historial:
            if t.suministro and t.suministro.item:
                items_en_historial.add(t.suministro.item)
        articulos_unicos = sorted(items_en_historial, key=lambda x: (x.name.lower(), x.reference.lower() if x.reference else ""))
        return articulos_unicos

    def get_headers_mapping(self):
        return {}

    def get_filename(self):
        return 'export.xlsx'
    
    def get_transacciones_historial(self, asset):
        transacciones = Transaction.objects.filter(Q(suministro__asset=asset) | Q(suministro_transf__asset=asset))
        if self.keyword_filter:
            transacciones = transacciones.filter(self.keyword_filter2)
        transacciones_historial = transacciones.order_by('-fecha')
        return transacciones_historial
    
    def redirect_with_next(self, request):
        next_url = request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return redirect(request.path)


class AssetSuministrosReportView(AssetInventoryBaseView):
    keyword_filter = Q(item__name__icontains='Combustible') | Q(item__name__icontains='Aceite') | Q(item__name__icontains='Filtro')
    keyword_filter2 = (Q(suministro__item__name__icontains='Combustible') | Q(suministro__item__name__icontains='Aceite') | Q(suministro__item__name__icontains='Filtro'))

    def get_context_data(self, request, asset, suministros, transacciones_historial, ultima_fecha_transaccion):
        context = super().get_context_data(request, asset, suministros, transacciones_historial, ultima_fecha_transaccion)
        # Agrupar suministros por presentación
        suministros = suministros.order_by('item__presentacion')
        grouped_suministros = {}
        for key, group in groupby(suministros, key=attrgetter('item.presentacion')):
            grouped_suministros[key] = list(group)
        context['grouped_suministros'] = grouped_suministros
        context['group_by'] = 'presentacion'

        items_en_historial = set()
        for t in transacciones_historial:
            if t.suministro and t.suministro.item:
                items_en_historial.add(t.suministro.item)

        # Convertir a lista y ordenar (opcional, según la preferencia):
        articulos_unicos = sorted(items_en_historial, key=lambda x: (x.name.lower(), x.reference.lower() if x.reference else ""))

        context['articulos_unicos'] = articulos_unicos
        return context

    def get_headers_mapping(self):
        return {
            'fecha': 'Fecha',
            'suministro__item__presentacion': 'Presentación',
            'suministro__item__name': 'Artículo',
            'cant': 'Cantidad',
            'tipo': 'Tipo',
            'user': 'Usuario',
            'motivo': 'Motivo',
            'cant_report': 'Cantidad Reportada',
        }

    def get_filename(self):
        return 'historial_suministros.xlsx'


class AssetInventarioReportView(AssetInventoryBaseView):
    keyword_filter = ~(Q(item__name__icontains='Combustible') | Q(item__name__icontains='Aceite') | Q(item__name__icontains='Filtro'))

    keyword_filter2 = ~(
        Q(suministro__item__name__icontains='Combustible')
        | Q(suministro__item__name__icontains='Aceite')
        | Q(suministro__item__name__icontains='Filtro')
    )

    def get_headers_mapping(self):
        return {
            'fecha': 'Fecha',
            'suministro__item__seccion': 'Categoría',
            'suministro__item__name': 'Artículo',
            'cant': 'Cantidad',
            'tipo': 'Tipo',
            'user': 'Usuario',
            'motivo': 'Motivo',
            'cant_report': 'Cantidad Reportada',
        }

    def get_filename(self):
        return 'historial_inventario.xlsx'

    def get_context_data(self, request, asset, suministros, transacciones_historial, ultima_fecha_transaccion):
        context = super().get_context_data(request, asset, suministros, transacciones_historial, ultima_fecha_transaccion)
        suministros = suministros.order_by('item__seccion')
        grouped_suministros = {}
        for key, group in groupby(suministros, key=attrgetter('item.seccion')):
            grouped_suministros[key] = list(group)
        context['grouped_suministros'] = grouped_suministros
        context['group_by'] = 'seccion'

        items_en_historial = set()
        for t in transacciones_historial:
            if t.suministro and t.suministro.item:
                items_en_historial.add(t.suministro.item)

        # Convertir a lista y ordenar (opcional, según la preferencia):
        articulos_unicos = sorted(items_en_historial, key=lambda x: (x.name.lower(), x.reference.lower() if x.reference else ""))

        context['articulos_unicos'] = articulos_unicos
        return context
    


@permission_required('got.delete_transaction', raise_exception=True)
def delete_transaction(request, transaction_id):
    transaccion = get_object_or_404(Transaction, id=transaction_id)
    next_url = request.POST.get('next', request.META.get('HTTP_REFERER', '/'))

    if request.method == 'POST':
        result = handle_delete_transaction(request, transaccion)
        if isinstance(result, HttpResponse):
            return result
        else:
            return redirect(next_url)
    else:
        return redirect(next_url)
    

# @permission_required('got.delete_transaction', raise_exception=True)
def delete_sumi(request, sumi_id):
    sumi = get_object_or_404(Suministro, id=sumi_id)
    next_url = request.POST.get('next', request.META.get('HTTP_REFERER', '/'))

    if request.method == 'POST':
        sumini = sumi.item
        sumi.delete()
        messages.success(request, f"Eliminado correctamente el articulo {sumini}")
        return redirect(next_url)
    else:
        messages.success(request, f"se intento y no fuciono")
        return redirect(next_url)


def export_historial_pdf(request, abbreviation):
    """
    Genera un PDF con los registros de transacciones,
    filtrados por rango de fechas y por artículos seleccionados,
    usando la plantilla base de PDF (`pdf_template.html`) y la función render_to_pdf.
    """
    asset = get_object_or_404(Asset, abbreviation=abbreviation)

    if request.method == 'POST':
        # 1) Obtener fechas (inicio y fin)
        fecha_inicio_str = request.POST.get('fecha_inicio', '')
        fecha_fin_str = request.POST.get('fecha_fin', '')

        # Parsear a objeto date, si no vienen => None
        fecha_inicio = None
        fecha_fin = None
        if fecha_inicio_str:
            try:
                fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            except:
                pass
        if fecha_fin_str:
            try:
                fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
            except:
                pass

        # 2) Artículos seleccionados (lista de IDs)
        items_seleccionados = request.POST.getlist('items_seleccionados')
        if not items_seleccionados:
            messages.error(request, "Debe seleccionar al menos un artículo para generar el PDF.")
            return redirect('inv:asset_inventario_report', abbreviation=abbreviation)

        # 3) Obtener transacciones base
        transacciones = Transaction.objects.filter(
            Q(suministro__asset=asset) | Q(suministro_transf__asset=asset)
        ).order_by('-fecha')

        # 4) Filtrar por rango de fechas
        if fecha_inicio and fecha_fin:
            transacciones = transacciones.filter(
                fecha__range=[fecha_inicio, fecha_fin]
            )
        elif fecha_inicio:
            transacciones = transacciones.filter(fecha__gte=fecha_inicio)
        elif fecha_fin:
            transacciones = transacciones.filter(fecha__lte=fecha_fin)

        # 5) Filtrar por items
        #   items_seleccionados => ID del item
        transacciones = transacciones.filter(
            Q(suministro__item__id__in=items_seleccionados) |
            Q(suministro_transf__item__id__in=items_seleccionados)
        )
        # 6) Obtener los suministros seleccionados
        suministros_seleccionados = Suministro.objects.filter(
            item__id__in=items_seleccionados,
            asset=asset
        )

        # 7) Calcular resúmenes por suministro
        suministros_summary = []
        for suministro in suministros_seleccionados:
            if fecha_inicio:
                trans_before_start = Transaction.objects.filter(suministro=suministro, fecha__lte=fecha_inicio).order_by('-fecha').first()
                cantidad_inicial = trans_before_start.cant_report if trans_before_start and trans_before_start.cant_report else Decimal('0.00')
            else:
                cantidad_inicial = Decimal('0.00')

            total_consumido = transacciones.filter(suministro=suministro, tipo='c').aggregate(total=Sum('cant'))['total'] or Decimal('0.00') # Total consumido: sum of 'c' transactions in the period
            total_ingresado_base = transacciones.filter(suministro=suministro, tipo='i').aggregate(total=Sum('cant'))['total'] or Decimal('0.00') # Total ingresado: suma de transacciones de tipo 'i'
            incoming_transfer = transacciones.filter(suministro_transf=suministro, tipo='t').aggregate(total=Sum('cant'))['total'] or Decimal('0.00') # Sumar también las transferencias entrantes (donde este suministro es el destino)
            total_ingresado = total_ingresado_base + incoming_transfer
            total_transfer_out = transacciones.filter(suministro=suministro, tipo='t').aggregate(total=Sum('cant'))['total'] or Decimal('0.00') # Total transferido a otros: suma de transferencias salientes (donde este suministro es el emisor)

            if fecha_fin: # Cantidad final: latest 'cant_report' before 'fecha_fin'
                trans_before_end = Transaction.objects.filter(suministro=suministro, fecha__lte=fecha_fin).order_by('-fecha').first()
                cantidad_final = trans_before_end.cant_report if trans_before_end and trans_before_end.cant_report else Decimal('0.00')
            else:
                # Si no hay fecha_fin, usar la última cantidad reportada hasta hoy
                trans_before_end = Transaction.objects.filter(suministro=suministro, fecha__lte=date.today()).order_by('-fecha').first()
                cantidad_final = trans_before_end.cant_report if trans_before_end and trans_before_end.cant_report else Decimal('0.00')

            suministros_summary.append({
                'suministro': suministro,
                'cantidad_inicial': cantidad_inicial,
                'total_consumido': total_consumido,
                'total_ingresado': total_ingresado,
                'total_transfer_out': total_transfer_out,
                'cantidad_final': cantidad_final,
            })

        # 8) Obtener los artículos seleccionados para el resumen en el header
        articulos_seleccionados = Item.objects.filter(id__in=items_seleccionados)

        data_context = {
            'asset': asset,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'transacciones': transacciones,
            'fecha_hoy': date.today(),
            'items': articulos_seleccionados,
            'suministros_summary': suministros_summary,
        }

        # 7) Renderizar con la plantilla PDF
        pdf = render_to_pdf('inventory_management/historial_pdf.html', data_context)
        if pdf:
            filename = f"Historial_{asset.abbreviation}.pdf"
            # inline => para abrir en navegador, attachment => para forzar descarga
            content = f"inline; filename='{filename}'"
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = content
            return response
        else:
            return HttpResponse("Error al generar el PDF", status=400)

    # Si no es POST, redirigir
    return redirect('inv:asset_inventario_report', abbreviation=abbreviation)
