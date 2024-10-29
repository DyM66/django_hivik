from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import permission_required, login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group, User
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Count, Q, OuterRef, Subquery, F, ExpressionWrapper, DateField, Prefetch, Sum, Max
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import get_template, render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.timezone import localdate
from django.views import generic, View
from django.views.decorators.cache import never_cache, cache_control
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.db import transaction as db_transaction
from datetime import timedelta, date, datetime
from xhtml2pdf import pisa
from io import BytesIO
import logging
import time
import base64
import uuid
import pandas as pd
import calendar
from django.utils.translation import gettext as _
from collections import OrderedDict
from itertools import groupby
from operator import attrgetter
from decimal import Decimal, InvalidOperation
from .functions import *
from .models import *
from .forms import *
from dateutil.relativedelta import relativedelta
from openpyxl.utils import get_column_letter
from datetime import datetime, time, date

logger = logging.getLogger(__name__)


@cache_control(max_age=86400)
def manifest(request):
    manifest_data = {
        "name": "GOT",
        "short_name": "GOT",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#FFFFFF",
        "theme_color": "#191645",
        "icons": [
            {
                "src": "https://hivik.s3.us-east-2.amazonaws.com/static/anchor-solid.svg",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "https://hivik.s3.us-east-2.amazonaws.com/static/anchor-solid.svg",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    }
    return JsonResponse(manifest_data)


@never_cache
def service_worker(request):
    js = '''
    // Código del Service Worker
    // Puedes dejarlo vacío si no necesitas funcionalidades adicionales
    self.addEventListener('install', function(event) {
        self.skipWaiting();
    });

    self.addEventListener('fetch', function(event) {
        // Manejo de fetch si es necesario
    });
    '''
    response = HttpResponse(js, content_type='application/javascript')
    return response


@login_required
def get_unapproved_requests_count(request):
    # Ajusta el filtro según tus necesidades y permisos
    count = Solicitud.objects.filter(approved=False).count()
    return JsonResponse({'count': count})


'ASSETS VIEWS'
class AssetsListView(LoginRequiredMixin, generic.ListView):

    model = Asset
    template_name = 'got/assets/asset_list.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.groups.filter(name='maq_members').exists():
            asset = Asset.objects.filter(
                models.Q(supervisor=request.user) | models.Q(capitan=request.user)
            ).first()

            if asset:
                return redirect('got:asset-detail', pk=asset.abbreviation)
        elif request.user.groups.filter(name='serport_members').exists():
            return redirect('got:my-tasks')
        else:
            return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        areas = {
            'a': 'Motonave',
            'b': 'Buceo',
            'o': 'Oceanografía',
            'l': 'Locativo',
            'v': 'Vehiculos',
            'x': 'Apoyo'
        }
        assets = Asset.objects.all()
        context['assets_by_area'] = {
            area_name: [asset for asset in assets if asset.area == area_code]
            for area_code, area_name in areas.items()
        }
        return context


class AssetDetailView(LoginRequiredMixin, generic.DetailView):

    model = Asset
    template_name = 'got/assets/asset_base.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset = self.get_object()
        user = self.request.user

        paginator = Paginator(get_full_systems(asset, user), 15)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        rotativos = Equipo.objects.filter(system__asset=asset, tipo='r').exists()
        
        context['rotativos'] = rotativos
        context['view_type'] = 'detail'
        context['consumibles'] = Suministro.objects.filter(asset=asset).exists()
        context['page_obj'] = page_obj
        context['items_by_subsystem'] = consumibles_summary(asset)
        context['fechas'] = fechas_range()
        context['consumos_grafica'] = consumos_combustible_asset(asset)
        context['horas_grafica'] = horas_total_asset(asset)
        context['sys_form'] = SysForm()

        return context

    def post(self, request, *args, **kwargs):
        asset = self.get_object()
        sys_form = SysForm(request.POST)
        
        if sys_form.is_valid():
            sys = sys_form.save(commit=False)
            sys.asset = asset
            sys.save()
            return redirect(request.path)
        else:
            context = {'asset': asset, 'sys_form': sys_form}
            return render(request, self.template_name, context)
        

class AssetMaintenancePlanView(LoginRequiredMixin, generic.DetailView):
    model = Asset
    template_name = 'got/assets/asset_base.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset = self.get_object()
        user = self.request.user

        filtered_rutas, current_month_name_es = self.get_filtered_rutas(asset, user)
        rotativos = Equipo.objects.filter(system__asset=asset, tipo='r').exists()

        context['rotativos'] = rotativos
        context['view_type'] = 'rutas'
        context['asset'] = asset
        context['mes'] = current_month_name_es
        context['page_obj_rutas'] = filtered_rutas
        context['rutinas_filter_form'] = RutinaFilterForm(self.request.GET or None, asset=asset)
        context['rutinas_disponibles'] = Ruta.objects.filter(system__asset=asset)
        return context

    def get_filtered_rutas(self, asset, user):
        form = RutinaFilterForm(self.request.GET or None, asset=asset)
        current_month_name_es = traductor(datetime.now().strftime('%B'))

        if form.is_valid():
            month = int(form.cleaned_data['month'])
            year = int(form.cleaned_data['year'])
            show_execute = form.cleaned_data.get('execute', False)
            selected_locations = form.cleaned_data.get('locations')
            current_month_name_es = traductor(calendar.month_name[month])
            
            filtered_rutas = Ruta.objects.filter(
                system__in=get_full_systems_ids(asset, user),
                system__location__in=selected_locations
            ).exclude(system__state__in=['x', 's']).order_by('-nivel', 'frecuency')

            if show_execute == 'on':
                filtered_rutas = [
                    ruta for ruta in filtered_rutas
                    if (ruta.next_date.month <= month and ruta.next_date.year <= year)
                    or (ruta.ot and ruta.ot.state == 'x')
                    or (ruta.percentage_remaining < 15)
                ]
            else:
                filtered_rutas = [
                    ruta for ruta in filtered_rutas
                    if (ruta.next_date.month <= month and ruta.next_date.year <= year)
                    or (ruta.percentage_remaining < 15)
                ]
        else:
            filtered_rutas = Ruta.objects.filter(
                system__in=get_full_systems_ids(asset, user)
            ).exclude(system__state__in=['x', 's']).order_by('-nivel', 'frecuency')
            filtered_rutas = [
                ruta for ruta in filtered_rutas
                if (ruta.percentage_remaining < 15)
            ]

        return filtered_rutas, current_month_name_es

    def post(self, request, *args, **kwargs):
        if 'download_excel' in request.POST:
            print('hola')
            return self.export_rutinas_to_excel()
        else:
            # Maneja otros casos si es necesario
            return redirect(request.path)

    def export_rutinas_to_excel(self):
        asset = self.get_object()
        user = self.request.user

        filtered_rutas, _ = self.get_filtered_rutas(asset, user)
        data = []

        for ruta in filtered_rutas:
            days_left = (ruta.next_date - datetime.now().date()).days if ruta.next_date else '---'
            data.append({
                'equipo_name': ruta.equipo.name if ruta.equipo else ruta.system.name,
                'location': ruta.equipo.system.location if ruta.equipo else ruta.system.location,
                'name': ruta.name,
                'frecuency': ruta.frecuency,
                'control': ruta.get_control_display(),
                'daysleft': days_left,
                'intervention_date': ruta.intervention_date.strftime('%d/%m/%Y') if ruta.intervention_date else '---',
                'next_date': ruta.next_date.strftime('%d/%m/%Y') if ruta.next_date else '---',
                'ot_num_ot': ruta.ot.num_ot if ruta.ot else '---',
                'activity': '---',
                'responsable': '' 
            })

            tasks = Task.objects.filter(ruta=ruta)
            for task in tasks:
                responsable_name = task.responsible.get_full_name() if task.responsible else '---'
                data.append({
                    'equipo_name': '',
                    'location': '',
                    'name': '',
                    'frecuency': '',
                    'control': '',
                    'daysleft': '',
                    'intervention_date': '',
                    'next_date': '',
                    'ot_num_ot': '',
                    'activity': f'- {task.description}', 
                    'responsable': responsable_name
                })

        df = pd.DataFrame(data)
        df.columns = ['Equipo', 'Ubicación', 'Código', 'Frecuencia', 'Control', 'Tiempo Restante', 'Última Intervención', 'Próxima Intervención', 'Orden de Trabajo', 'Actividad', 'Responsable']
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="rutinas.xlsx"'
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        return response


def preventivo_pdf(request, pk):
    asset = get_object_or_404(Asset, pk=pk)

    month = request.GET.get('month')
    year = request.GET.get('year')
    show_execute = request.GET.get('execute', False)
    selected_locations = request.GET.getlist('locations')
    systems = get_full_systems_ids(asset, request.user)
    filtered_rutas = Ruta.objects.filter(system__in=systems).exclude(system__state__in=['x', 's']).order_by('-nivel', 'frecuency')

    if selected_locations:
        filtered_rutas = filtered_rutas.filter(system__location__in=selected_locations)

    if month and year:
        month = int(month)
        year = int(year)
        if show_execute == 'on':
            filtered_rutas = [ruta for ruta in filtered_rutas if (ruta.next_date.month <= month or ruta.next_date.year <= year) or (ruta.ot and ruta.ot.state == 'x') or (ruta.percentage_remaining < 15)]
        else:
            filtered_rutas = [ruta for ruta in filtered_rutas if (ruta.next_date.month <= month or ruta.next_date.year <= year) or (ruta.percentage_remaining < 15)]

    current_month_name_es = traductor(calendar.month_name[month]) if month else traductor(datetime.now().strftime('%B'))

    context = {
        'rq': asset,
        'filtered_rutas': filtered_rutas,
        'mes': current_month_name_es,
    }

    return render_to_pdf('got/assets/asset-routine.html', context)


class AssetDocCreateView(generic.View):
    form_class = DocumentForm
    template_name = 'got/assets/add-document.html'

    def get(self, request, asset_id):
        asset = get_object_or_404(Asset, pk=asset_id)
        form = self.form_class()
        return render(request, self.template_name, {'form': form, 'asset': asset})

    def post(self, request, asset_id):
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.asset = get_object_or_404(Asset, pk=asset_id)
            document.modified_by = request.user
            document.save()
            return redirect('got:asset-detail', pk=asset_id)
        return render(request, self.template_name, {'form': form})


def asset_suministros_report(request, abbreviation):

    

    asset = get_object_or_404(Asset, abbreviation=abbreviation)
    keyword_filter = Q(item__name__icontains='Combustible') | Q(item__name__icontains='Aceite') | Q(item__name__icontains='Filtro')
    suministros = Suministro.objects.filter(asset=asset, item__seccion='c').filter(keyword_filter).select_related('item').order_by('item__presentacion')

    motonaves = Asset.objects.filter(Q(area='a') | Q(area='l'))

    grouped_suministros = {}
    for key, group in groupby(suministros, key=attrgetter('item.presentacion')):
        grouped_suministros[key] = list(group)

    ultima_fecha_transaccion = Transaction.objects.filter(suministro__asset=asset).aggregate(Max('fecha'))['fecha__max'] or "---"
    transacciones_historial = Transaction.objects.filter(
        Q(suministro__asset=asset) | Q(suministro_transf__asset=asset)
    ).order_by('-fecha')


    if request.method == 'POST' and 'download_excel' in request.POST:
        df = pd.DataFrame(list(transacciones_historial.values(
            'fecha',
            'suministro__item__presentacion',
            'suministro__item__name',
            'cant',
            'tipo',
            'user',
            'motivo',
            'cant_report',
        )))
        df.rename(columns={
            'fecha': 'Fecha',
            'suministro__item__presentacion': 'Presentación',
            'suministro__item__name': 'Artículo',
            'cant': 'Cantidad',
            'tipo': 'Tipo',
            'user': 'Usuario',
            'motivo': 'Motivo',
            'cant_report': 'Cantidad Reportada',
        }, inplace=True)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="historial_suministros.xlsx"'
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        return response

    if request.method == 'POST' and 'transfer_suministro_id' in request.POST:
    
        suministro_id = request.POST.get('transfer_suministro_id')
        transfer_cantidad_str = request.POST.get('transfer_cantidad', '0') or '0'
        destination_asset_id = request.POST.get('destination_asset_id')
        transfer_motivo = request.POST.get('transfer_motivo', '')
        transfer_fecha_str = request.POST.get('transfer_fecha', '')  # New field
        confirm_overwrite = request.POST.get('confirm_overwrite', 'no')

        operation = Operation.objects.filter(
            asset=asset,
            confirmado=True,
            start__lte=transfer_fecha,
            end__gte=transfer_fecha
        ).first()

        if operation:
            transfer_motivo = f"{transfer_motivo} - {operation.proyecto}"

        try:
            transfer_fecha = datetime.strptime(transfer_fecha_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Fecha inválida.')
            return redirect(reverse('got:asset_suministros_report', kwargs={'abbreviation': asset.abbreviation}))

        try:
            transfer_cantidad = Decimal(transfer_cantidad_str)
        except InvalidOperation:
            messages.error(request, 'Cantidad inválida.')
            return redirect(reverse('got:asset_suministros_report', kwargs={'abbreviation': asset.abbreviation}))

        if transfer_cantidad <= 0:
            messages.error(request, 'La cantidad a transferir debe ser mayor a cero.')
            return redirect(reverse('got:asset_suministros_report', kwargs={'abbreviation': asset.abbreviation}))

        suministro_origen = get_object_or_404(Suministro, id=suministro_id, asset=asset)

        if transfer_cantidad > suministro_origen.cantidad:
            messages.error(request, 'La cantidad a transferir no puede ser mayor a la cantidad disponible.')
            return redirect(reverse('got:asset_suministros_report', kwargs={'abbreviation': asset.abbreviation}))

        existing_transaction = None
        try:
            existing_transaction = Transaction.objects.get(
                suministro=suministro_origen,
                fecha=transfer_fecha,
                tipo='t'
            )
        except Transaction.DoesNotExist:
            pass

        if existing_transaction and confirm_overwrite != 'yes':
            context = {
                'asset': asset,
                'suministros': suministros,
                'overwriting_transactions': [('Transferencia', existing_transaction)],
                'post_data': request.POST,
            }
            return render(request, 'got/assets/confirm_overwrite.html', context)

        # Obtener el barco destino
        destination_asset = get_object_or_404(Asset, abbreviation=destination_asset_id)

        suministro_destino, _ = Suministro.objects.get_or_create(
            asset=destination_asset,
            item=suministro_origen.item,
            defaults={'cantidad': Decimal('0.00')}
        )

        if existing_transaction:
            suministro_origen.cantidad += existing_transaction.cant
            suministro_destino.cantidad -= existing_transaction.cant

            suministro_origen.cantidad -= transfer_cantidad
            suministro_destino.cantidad += transfer_cantidad

            suministro_origen.save()
            suministro_destino.save()

            existing_transaction.cant = transfer_cantidad
            existing_transaction.user = request.user.get_full_name()
            existing_transaction.motivo = transfer_motivo
            existing_transaction.cant_report = suministro_origen.cantidad
            existing_transaction.cant_report_transf = suministro_destino.cantidad
            existing_transaction.suministro_transf = suministro_destino
            existing_transaction.save()

        else:
            # Update quantities
            suministro_origen.cantidad -= transfer_cantidad
            suministro_destino.cantidad += transfer_cantidad
            
            suministro_origen.save()
            suministro_destino.save()

            Transaction.objects.create(
                suministro=suministro_origen,
                cant=transfer_cantidad,
                fecha=transfer_fecha,
                user=request.user.get_full_name(),
                motivo=transfer_motivo,
                tipo='t',
                cant_report=suministro_origen.cantidad,
                suministro_transf=suministro_destino,
                cant_report_transf=suministro_destino.cantidad
            )

        messages.success(request, f'Se ha transferido {transfer_cantidad} {suministro_origen.item.presentacion} de {suministro_origen.item.name} al barco {destination_asset.name}.')
        return redirect(reverse('got:asset-suministros', kwargs={'abbreviation': asset.abbreviation}))

    elif request.method == 'POST':
    
        fecha_reporte = request.POST.get('fecha_reporte', timezone.now().date())
        confirm_overwrite = request.POST.get('confirm_overwrite', 'no')
        overwriting_transactions = []

        operation = Operation.objects.filter(
            asset=asset,
            confirmado=True,
            start__lte=fecha_reporte,
            end__gte=fecha_reporte
        ).first()

        if operation:
            motivo = operation.proyecto
        else:
            motivo = ''

        for suministro in suministros:
            cantidad_consumida_str = request.POST.get(f'consumido_{suministro.id}', '0') or '0'
            cantidad_ingresada_str = request.POST.get(f'ingresado_{suministro.id}', '0') or '0'

            try:
                cantidad_consumida = Decimal(cantidad_consumida_str)
            except InvalidOperation:
                cantidad_consumida = Decimal('0')

            try:
                cantidad_ingresada = Decimal(cantidad_ingresada_str)
            except InvalidOperation:
                cantidad_ingresada = Decimal('0')

            if cantidad_consumida == Decimal('0') and cantidad_ingresada == Decimal('0'):
                continue

            existing_transactions = []

            if cantidad_ingresada > Decimal('0'):
                try:
                    existing_ingreso = Transaction.objects.get(
                        suministro=suministro,
                        fecha=fecha_reporte,
                        tipo='i'
                    )
                    existing_transactions.append(('Ingreso', existing_ingreso))
                except Transaction.DoesNotExist:
                    pass

            # Check for existing Consumo transaction
            if cantidad_consumida > Decimal('0'):
                try:
                    existing_consumo = Transaction.objects.get(
                        suministro=suministro,
                        fecha=fecha_reporte,
                        tipo='c'
                    )
                    existing_transactions.append(('Consumo', existing_consumo))
                except Transaction.DoesNotExist:
                    pass

            if existing_transactions and confirm_overwrite != 'yes':
                overwriting_transactions.extend(existing_transactions)

        if overwriting_transactions and confirm_overwrite != 'yes':
            # Render the warning template
            context = {
                'asset': asset,
                'suministros': suministros,
                'overwriting_transactions': overwriting_transactions,
                'post_data': request.POST,
            }
            return render(request, 'got/assets/confirm_overwrite.html', context)
        else:
            for suministro in suministros:
                cantidad_consumida_str = request.POST.get(f'consumido_{suministro.id}', '0') or '0'
                cantidad_ingresada_str = request.POST.get(f'ingresado_{suministro.id}', '0') or '0'

                try:
                    cantidad_consumida = Decimal(cantidad_consumida_str)
                except InvalidOperation:
                    cantidad_consumida = Decimal('0')

                try:
                    cantidad_ingresada = Decimal(cantidad_ingresada_str)
                except InvalidOperation:
                    cantidad_ingresada = Decimal('0')

                if cantidad_consumida == Decimal('0') and cantidad_ingresada == Decimal('0'):
                    continue

                # Handle Ingreso
                if cantidad_ingresada > Decimal('0'):
                    suministro, _ = Suministro.objects.get_or_create(asset=asset, item=suministro.item)
                    try:
                        transaccion_ingreso = Transaction.objects.get(
                            suministro=suministro,
                            fecha=fecha_reporte,
                            tipo='i'
                        )
                        # Reverse previous effect
                        suministro.cantidad -= transaccion_ingreso.cant
                        # Update transaction
                        transaccion_ingreso.cant = cantidad_ingresada
                        transaccion_ingreso.user = request.user.get_full_name()
                        transaccion_ingreso.motivo = motivo
                        transaccion_ingreso.cant_report = suministro.cantidad + cantidad_ingresada
                        transaccion_ingreso.save()
                    except Transaction.DoesNotExist:
                        transaccion_ingreso = Transaction.objects.create(
                            suministro=suministro,
                            cant=cantidad_ingresada,
                            fecha=fecha_reporte,
                            user=request.user.get_full_name(),
                            motivo=motivo,
                            tipo='i',
                            cant_report=suministro.cantidad + cantidad_ingresada
                        )

                    suministro.cantidad += cantidad_ingresada
                    suministro.save()

                # Handle Consumo
                if cantidad_consumida > Decimal('0'):
                    suministro, _ = Suministro.objects.get_or_create(asset=asset, item=suministro.item)
                    try:
                        transaccion_consumo = Transaction.objects.get(
                            suministro=suministro,
                            fecha=fecha_reporte,
                            tipo='c'
                        )
                        # Reverse previous effect
                        suministro.cantidad += transaccion_consumo.cant
                        # Update transaction
                        transaccion_consumo.cant = cantidad_consumida
                        transaccion_consumo.user = request.user.get_full_name()
                        transaccion_consumo.motivo = motivo
                        transaccion_consumo.cant_report = suministro.cantidad - cantidad_consumida
                        transaccion_consumo.save()
                    except Transaction.DoesNotExist:
                        transaccion_consumo = Transaction.objects.create(
                            suministro=suministro,
                            cant=cantidad_consumida,
                            fecha=fecha_reporte,
                            user=request.user.get_full_name(),
                            motivo=motivo,
                            tipo='c',
                            cant_report=suministro.cantidad - cantidad_consumida
                        )
                    # Update supply quantity
                    suministro.cantidad -= cantidad_consumida
                    suministro.save()

            messages.success(request, 'Completado')
            return redirect(reverse('got:asset-suministros', kwargs={'abbreviation': asset.abbreviation}))

    transacciones_por_presentacion = {}
    for presentacion, suministros_group in grouped_suministros.items():
        transacciones_por_presentacion[presentacion] = transacciones_historial.filter(suministro__in=suministros_group)

    articles = sorted(set(
        [transaccion.suministro.item.name for transaccion in transacciones_historial if transaccion.suministro and transaccion.suministro.asset == asset] +
        [transaccion.suministro_transf.item.name for transaccion in transacciones_historial if transaccion.suministro_transf and transaccion.suministro_transf.asset == asset]
    ))

    context = {
        'asset': asset, 
        'suministros': suministros, 
        'grouped_suministros': grouped_suministros,
        'ultima_fecha_transaccion': ultima_fecha_transaccion,
        'transacciones_historial': transacciones_historial,
        'transacciones_por_presentacion': transacciones_por_presentacion,
        'fecha_actual': timezone.now().date(),
        'articles': articles,
        'motonaves': motonaves,
        }

    return render(request, 'got/assets/asset_suministros_report.html', context)


def asset_inventario_report(request, abbreviation):
    asset = get_object_or_404(Asset, abbreviation=abbreviation)

    keyword_filter = ~(
        Q(item__name__icontains='Combustible') | 
        Q(item__name__icontains='Aceite') | 
        Q(item__name__icontains='Filtro')
    )
    suministros = Suministro.objects.filter(asset=asset).filter(keyword_filter).select_related('item').order_by('item__seccion')

    motonaves = Asset.objects.filter(area='a')

    # Agrupar suministros por la categoría del artículo (seccion)
    grouped_suministros = {}
    for key, group in groupby(suministros, key=attrgetter('item.seccion')):
        grouped_suministros[key] = list(group)

    transacciones_historial = Transaction.objects.filter(
        Q(suministro__asset=asset) | Q(suministro_transf__asset=asset),
        Q(suministro__in=suministros) | Q(suministro_transf__in=suministros)
    ).order_by('-fecha')

    # Obtener la última fecha de transacción
    ultima_fecha_transaccion = transacciones_historial.aggregate(Max('fecha'))['fecha__max'] or "---"

    # Obtener el diccionario de secciones para mostrar los nombres completos en la plantilla
    secciones_dict = dict(Item.SECCION)

    articles = sorted(set(
        transaccion.suministro.item.name if transaccion.suministro and transaccion.suministro.asset == asset else transaccion.suministro_transf.item.name
        for transaccion in transacciones_historial
    ))

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'add_suministro' and request.user.has_perm('got.can_add_supply'):
            # Manejar la creación de un nuevo suministro
            item_id = request.POST.get('item_id')
            item = get_object_or_404(Item, id=item_id)

            # Verificar si el suministro ya existe
            suministro_existente = Suministro.objects.filter(asset=asset, item=item).exists()
            if suministro_existente:
                messages.error(request, f'El suministro para el artículo "{item.name}" ya existe en este asset.')
            else:
                Suministro.objects.create(
                    item=item,
                    cantidad=Decimal('0.00'),
                    asset=asset
                )
                messages.success(request, f'Suministro para "{item.name}" creado exitosamente.')
            return redirect(reverse('got:asset_inventario_report', kwargs={'abbreviation': asset.abbreviation}))
    
        elif 'transfer_suministro_id' in request.POST:
            # Manejar la transferencia
            suministro_id = request.POST.get('transfer_suministro_id')
            transfer_cantidad_str = request.POST.get('transfer_cantidad', '0') or '0'
            destination_asset_id = request.POST.get('destination_asset_id')
            transfer_motivo = request.POST.get('transfer_motivo', '')
            transfer_fecha_str = request.POST.get('transfer_fecha', '')  # New field
            confirm_overwrite = request.POST.get('confirm_overwrite', 'no')

            try:
                transfer_fecha = datetime.strptime(transfer_fecha_str, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Fecha inválida.')
                return redirect(reverse('got:asset_inventario_report', kwargs={'abbreviation': asset.abbreviation}))

            try:
                transfer_cantidad = Decimal(transfer_cantidad_str)
            except InvalidOperation:
                messages.error(request, 'Cantidad inválida.')
                return redirect(reverse('got:asset_inventario_report', kwargs={'abbreviation': asset.abbreviation}))

            if transfer_cantidad <= 0:
                messages.error(request, 'La cantidad a transferir debe ser mayor a cero.')
                return redirect(reverse('got:asset_inventario_report', kwargs={'abbreviation': asset.abbreviation}))

            suministro_origen = get_object_or_404(Suministro, id=suministro_id, asset=asset)

            if transfer_cantidad > suministro_origen.cantidad:
                messages.error(request, 'La cantidad a transferir no puede ser mayor a la cantidad disponible.')
                return redirect(reverse('got:asset_inventario_report', kwargs={'abbreviation': asset.abbreviation}))

            existing_transaction = None
            try:
                existing_transaction = Transaction.objects.get(
                    suministro=suministro_origen,
                    fecha=transfer_fecha,
                    tipo='t'
                )
            except Transaction.DoesNotExist:
                pass

            if existing_transaction and confirm_overwrite != 'yes':
                # Prepare data for confirmation modal
                context = {
                    'asset': asset,
                    'suministros': suministros,
                    'overwriting_transactions': [('Transferencia', existing_transaction)],
                    'post_data': request.POST,
                }
                return render(request, 'got/assets/confirm_overwrite.html', context)
            else:
                destination_asset = get_object_or_404(Asset, abbreviation=destination_asset_id)

                suministro_destino, _ = Suministro.objects.get_or_create(
                    asset=destination_asset,
                    item=suministro_origen.item,
                    defaults={'cantidad': Decimal('0.00')}
                )

                if existing_transaction:
                    # Revert previous quantities
                    suministro_origen.cantidad += existing_transaction.cant
                    suministro_destino.cantidad -= existing_transaction.cant

                suministro_origen.cantidad -= transfer_cantidad
                suministro_destino.cantidad += transfer_cantidad

                suministro_origen.save()
                suministro_destino.save()

                if existing_transaction:
                    # Update existing transaction
                    existing_transaction.cant = transfer_cantidad
                    existing_transaction.user = request.user.get_full_name()
                    existing_transaction.motivo = transfer_motivo
                    existing_transaction.cant_report = suministro_origen.cantidad
                    existing_transaction.cant_report_transf = suministro_destino.cantidad
                    existing_transaction.suministro_transf = suministro_destino
                    existing_transaction.save()
                else:
                    # Create Transaction of type 't'
                    Transaction.objects.create(
                        suministro=suministro_origen,
                        cant=transfer_cantidad,
                        fecha=transfer_fecha,
                        user=request.user.get_full_name(),
                        motivo=transfer_motivo,
                        tipo='t',
                        cant_report=suministro_origen.cantidad,
                        suministro_transf=suministro_destino,
                        cant_report_transf=suministro_destino.cantidad
                    )

                messages.success(request, f'Se ha transferido {transfer_cantidad} {suministro_origen.item.presentacion} de {suministro_origen.item.name} al barco {destination_asset.name}.')
                return redirect(reverse('got:asset_inventario_report', kwargs={'abbreviation': asset.abbreviation}))

        elif 'download_excel' in request.POST:
            # Lógica para descargar Excel
            df = pd.DataFrame(list(transacciones_historial.values(
                'fecha',
                'suministro__item__seccion',
                'suministro__item__name',
                'cant',
                'tipo',
                'user',
                'motivo',
                'cant_report',
            )))
            df.rename(columns={
                'fecha': 'Fecha',
                'suministro__item__seccion': 'Categoría',
                'suministro__item__name': 'Artículo',
                'cant': 'Cantidad',
                'tipo': 'Tipo',
                'user': 'Usuario',
                'motivo': 'Motivo',
                'cant_report': 'Cantidad Reportada',
            }, inplace=True)
            df['Categoría'] = df['Categoría'].map(secciones_dict)
            response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="historial_inventario.xlsx"'
            with pd.ExcelWriter(response, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            return response

        else:
            fecha_reporte = request.POST.get('fecha_reporte', timezone.now().date())
            confirm_overwrite = request.POST.get('confirm_overwrite', 'no')
            overwriting_transactions = []

            for suministro in suministros:
                cantidad_consumida_str = request.POST.get(f'consumido_{suministro.id}', '0') or '0'
                cantidad_ingresada_str = request.POST.get(f'ingresado_{suministro.id}', '0') or '0'

                try:
                    cantidad_consumida = Decimal(cantidad_consumida_str)
                except InvalidOperation:
                    cantidad_consumida = Decimal('0')

                try:
                    cantidad_ingresada = Decimal(cantidad_ingresada_str)
                except InvalidOperation:
                    cantidad_ingresada = Decimal('0')

                if cantidad_consumida == Decimal('0') and cantidad_ingresada == Decimal('0'):
                    continue

                existing_transactions = []

                if cantidad_ingresada > Decimal('0'):
                    try:
                        existing_ingreso = Transaction.objects.get(
                            suministro=suministro,
                            fecha=fecha_reporte,
                            tipo='i'
                        )
                        existing_transactions.append(('Ingreso', existing_ingreso))
                    except Transaction.DoesNotExist:
                        pass

                if cantidad_consumida > Decimal('0'):
                    try:
                        existing_consumo = Transaction.objects.get(
                            suministro=suministro,
                            fecha=fecha_reporte,
                            tipo='c'
                        )
                        existing_transactions.append(('Consumo', existing_consumo))
                    except Transaction.DoesNotExist:
                        pass

            if overwriting_transactions and confirm_overwrite != 'yes':
                # Render the warning template
                context = {
                    'asset': asset,
                    'suministros': suministros,
                    'overwriting_transactions': overwriting_transactions,
                    'post_data': request.POST,
                }
                return render(request, 'got/assets/confirm_overwrite.html', context)
            else:
                for suministro in suministros:
                    cantidad_consumida_str = request.POST.get(f'consumido_{suministro.id}', '0') or '0'
                    cantidad_ingresada_str = request.POST.get(f'ingresado_{suministro.id}', '0') or '0'

                    try:
                        cantidad_consumida = Decimal(cantidad_consumida_str)
                    except InvalidOperation:
                        cantidad_consumida = Decimal('0')

                    try:
                        cantidad_ingresada = Decimal(cantidad_ingresada_str)
                    except InvalidOperation:
                        cantidad_ingresada = Decimal('0')

                    if cantidad_consumida == Decimal('0') and cantidad_ingresada == Decimal('0'):
                        continue

                    # Handle Ingreso
                    if cantidad_ingresada > Decimal('0'):
                        suministro, _ = Suministro.objects.get_or_create(asset=asset, item=suministro.item)
                        try:
                            transaccion_ingreso = Transaction.objects.get(
                                suministro=suministro,
                                fecha=fecha_reporte,
                                tipo='i'
                            )
                            suministro.cantidad -= transaccion_ingreso.cant
                            # Update transaction
                            transaccion_ingreso.cant = cantidad_ingresada
                            transaccion_ingreso.user = request.user.get_full_name()
                            transaccion_ingreso.motivo = request.POST.get('motivo', '')
                            transaccion_ingreso.cant_report = suministro.cantidad + cantidad_ingresada
                            transaccion_ingreso.save()
                        except Transaction.DoesNotExist:
                            transaccion_ingreso = Transaction.objects.create(
                                suministro=suministro,
                                cant=cantidad_ingresada,
                                fecha=fecha_reporte,
                                user=request.user.get_full_name(),
                                motivo=request.POST.get('motivo', ''),
                                tipo='i',
                                cant_report=suministro.cantidad + cantidad_ingresada
                            )
                        suministro.cantidad += cantidad_ingresada
                        suministro.save()

                    # Handle Consumo
                    if cantidad_consumida > Decimal('0'):
                        suministro, _ = Suministro.objects.get_or_create(asset=asset, item=suministro.item)
                        try:
                            transaccion_consumo = Transaction.objects.get(
                                suministro=suministro,
                                fecha=fecha_reporte,
                                tipo='c'
                            )
                            # Reverse previous effect
                            suministro.cantidad += transaccion_consumo.cant
                            # Update transaction
                            transaccion_consumo.cant = cantidad_consumida
                            transaccion_consumo.user = request.user.get_full_name()
                            transaccion_consumo.motivo = request.POST.get('motivo', '')
                            transaccion_consumo.cant_report = suministro.cantidad - cantidad_consumida
                            transaccion_consumo.save()
                        except Transaction.DoesNotExist:
                            transaccion_consumo = Transaction.objects.create(
                                suministro=suministro,
                                cant=cantidad_consumida,
                                fecha=fecha_reporte,
                                user=request.user.get_full_name(),
                                motivo=request.POST.get('motivo', ''),
                                tipo='c',
                                cant_report=suministro.cantidad - cantidad_consumida
                            )
                        # Update supply quantity
                        suministro.cantidad -= cantidad_consumida
                        suministro.save()

                messages.success(request, 'Inventario actualizado exitosamente.')
                return redirect(reverse('got:asset_inventario_report', kwargs={'abbreviation': asset.abbreviation}))
            
    existing_item_ids = suministros.values_list('item_id', flat=True)
    available_items = Item.objects.exclude(id__in=existing_item_ids)

    context = {
        'asset': asset,
        'suministros': suministros,
        'grouped_suministros': grouped_suministros,
        'ultima_fecha_transaccion': ultima_fecha_transaccion,
        'transacciones_historial': transacciones_historial,
        'fecha_actual': timezone.now().date(),
        'motonaves': motonaves,
        'secciones_dict': secciones_dict,
        'articles': articles,
        'available_items': available_items,
    }

    return render(request, 'got/assets/asset_inventario_report.html', context)


@permission_required('got.delete_transaction', raise_exception=True)
def delete_transaction(request, transaction_id):
    transaccion = get_object_or_404(Transaction, id=transaction_id)
    next_url = request.POST.get('next', '')

    if request.method == 'POST':
        with db_transaction.atomic():
            # Revert quantities based on transaction type
            if transaccion.tipo in ['i', 'c']:
                suministro = transaccion.suministro
                if transaccion.tipo == 'i':
                    # Revert an Ingreso: subtract the quantity from the suministro
                    suministro.cantidad -= transaccion.cant
                elif transaccion.tipo == 'c':
                    # Revert a Consumo: add the quantity back to the suministro
                    suministro.cantidad += transaccion.cant
                suministro.save()
            elif transaccion.tipo == 't':
                # Revert quantities in both source and destination suministros
                suministro_origen = transaccion.suministro
                suministro_destino = transaccion.suministro_transf

                # Revert the quantities
                suministro_origen.cantidad += transaccion.cant
                suministro_destino.cantidad -= transaccion.cant

                suministro_origen.save()
                suministro_destino.save()
            else:
                # Handle other types if necessary
                pass

            # Delete the transaction
            transaccion.delete()

        messages.success(request, 'La transacción ha sido eliminada y las cantidades han sido actualizadas.')
        return redirect(next_url)
    else:
        # If not POST, redirect back to the previous page
        return redirect(next_url)


@login_required
def schedule(request, pk):
    asset = Asset.objects.get(pk=pk)
    systems = asset.system_set.all()

    routines_by_system = OrderedDict()
    for system in systems:
        routines = system.rutas.all()
        if routines.exists():
            routines_by_system[system] = [
                {
                    'routine': routine,
                    'repeticiones': calcular_repeticiones2(routine, 'anual')[0],
                    'meses_ejecucion': calcular_repeticiones2(routine, 'anual')[1],
                } 
                for routine in routines
            ]

    current_date = datetime.now()
    months = []
    months_with_year = []
    year_months = OrderedDict()

    for i in range(13):  # De este mes hasta 12 meses después
        month = (current_date.month + i - 1) % 12 + 1
        year = current_date.year + (current_date.month + i - 1) // 12
        month_name = _(calendar.month_name[month]).capitalize()
        months.append(month_name)
        month_name_with_year = f"{calendar.month_name[month]} {year}"
        months_with_year.append(month_name_with_year)
        if year not in year_months:
            year_months[year] = []
        year_months[year].append(month_name)

    context = {
        'asset': asset,
        'routines_by_system': routines_by_system,
        'months': months,
        'months_with_year': months_with_year,
        'year_months': year_months,
    }
    return render(request, 'got/schedule.html', context)


def generate_asset_pdf(request, asset_id):
    asset = get_object_or_404(Asset, pk=asset_id)
    location_based_systems = System.objects.filter(location=asset.name).exclude(asset=asset).order_by('group')

    location_based_systems = [system for system in location_based_systems if system.equipos.exists()]
    direct_systems = asset.system_set.all().order_by('group')

    direct_systems = [system for system in direct_systems if system.equipos.exists()]
    all_systems = location_based_systems + direct_systems

    context = {
        'asset': asset,
        'systems': all_systems,
    }

    return render_to_pdf('got/assets/asset_pdf_template.html', context)


def acta_entrega_pdf(request, pk):
    equipo = get_object_or_404(Equipo, pk=pk)
    current_date = timezone.localdate()
    context = {
        'equipo': equipo,
        'current_date': current_date,
    }

    return render_to_pdf('got/systems/acta-entrega.html', context)


'SYSTEMS VIEW'
class SysDetailView(LoginRequiredMixin, generic.DetailView):

    model = System
    template_name = "got/systems/system_detail.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        system = self.get_object()
        context['is_structures'] = system.name.lower() == "estructuras"
        
        orders_list = Ot.objects.filter(system=system)
        view_type = self.kwargs.get('view_type', 'sys')
        context['view_type'] = view_type

        if view_type == 'sys':
            paginator = Paginator(orders_list, 10)
        else:
            paginator = Paginator(orders_list, 4)

        page = self.request.GET.get('page')
        try:
            orders = paginator.page(page)
        except PageNotAnInteger:
            orders = paginator.page(1)
        except EmptyPage:
            orders = paginator.page(paginator.num_pages)
        context['orders'] = orders

        try:
            equipment = Equipo.objects.get(code=view_type)
            transferencias = Transferencia.objects.filter(equipo=equipment).order_by('-fecha')
            context['equipo'] = equipment
            context['transferencias'] = transferencias
            context['suministros'] = Suministro.objects.filter(equipo=equipment)
        except Equipo.DoesNotExist:
            equipments = Equipo.objects.filter(system=system, subsystem=view_type)
            context['equipos'] = equipments

        subsystems = Equipo.objects.filter(system=system).exclude(subsystem__isnull=True).exclude(subsystem__exact='').values_list('subsystem', flat=True)
        context['unique_subsystems'] = list(set(subsystems))
        context['items'] = Item.objects.all()
        return context
    

class SysUpdate(UpdateView):

    model = System
    form_class = SysForm
    template_name = 'got/systems/system_form.html'

    def form_valid(self, form):
        system = form.save(commit=False)
        system.modified_by = self.request.user
        system.save()
        return super().form_valid(form)


class SysDelete(DeleteView):

    model = System

    def delete(self, request, *args, **kwargs):
        system = self.get_object()
        system.modified_by = request.user

        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        asset_code = self.object.asset.abbreviation
        success_url = reverse_lazy(
            'got:asset-detail', kwargs={'pk': asset_code})
        return str(success_url)
    

def system_maintence_pdf(request, asset_id, system_id):
    asset = get_object_or_404(Asset, pk=asset_id)
    system = get_object_or_404(System, pk=system_id, asset=asset)
    start_date = timezone.now()

    sections = [
        {'title': 'Resumen', 'id': 'summary'},
        {'title': 'Información del Sistema', 'id': 'system-info'},
        {'title': 'Equipos Asociados', 'id': 'associated-equipment'},
        {'title': 'Rutinas de Mantenimiento', 'id': 'maintenance-routines'},
        {'title': 'Bitácora de Mantenimientos', 'id': 'maintenance-log'},
    ]

    context = {
        'asset': asset,
        'system': system,
        'sections': sections,
        'current_date': start_date,
    }

    return render_to_pdf('got/systems/system_pdf_template.html', context)


'EQUIPMENTS VIEW'
class EquipoCreateView(LoginRequiredMixin, CreateView):

    model = Equipo
    form_class = EquipoForm
    template_name = 'got/systems/equipo_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['upload_form'] = UploadImages(self.request.POST, self.request.FILES)
        else:
            context['upload_form'] = UploadImages()
        return context

    def form_valid(self, form):
        system = System.objects.get(pk=self.kwargs['pk'])
        form.instance.system = system
        asset_abbreviation = system.asset.abbreviation
        group_number = system.group
        tipo = form.cleaned_data['tipo'].upper()

        similar_equipments = Equipo.objects.filter(
            code__startswith=f"{asset_abbreviation}-{group_number}-{tipo}"
        )
        sequence_number = similar_equipments.count() + 1
        sequence_str = str(sequence_number).zfill(3) 
        generated_code = f"{asset_abbreviation}-{group_number}-{tipo}-{sequence_str}"
        form.instance.code = generated_code
        form.instance.modified_by = self.request.user
        response = super().form_valid(form)

        upload_form = self.get_context_data()['upload_form']
        if upload_form.is_valid():
            for file in self.request.FILES.getlist('file_field'):
                Image.objects.create(image=file, equipo=self.object)

        return response

    def get_success_url(self):
        return reverse('got:sys-detail', kwargs={'pk': self.object.system.pk})
    

class EquipoUpdate(UpdateView):

    model = Equipo
    form_class = EquipoForm
    template_name = 'got/systems/equipo_form.html'
    http_method_names = ['get', 'post']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['upload_form'] = UploadImages(self.request.POST, self.request.FILES)
        else:
            context['upload_form'] = UploadImages()
        context['image_formset'] = modelformset_factory(Image, fields=('image',), extra=0)(queryset=self.object.images.all())
        return context
    
    def form_valid(self, form):
        form.instance.modified_by = self.request.user
        response = super().form_valid(form)
        upload_form = self.get_context_data()['upload_form']

        if upload_form.is_valid():
            for file in self.request.FILES.getlist('file_field'):
                Image.objects.create(image=file, equipo=self.object)
                print(file)
        return response

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if "delete_image" in request.POST:
            image_id = request.POST.get("delete_image")
            Image.objects.filter(id=image_id).delete()
            return redirect(self.get_success_url())
        return super().post(request, *args, **kwargs)

class EquipoDelete(DeleteView):

    model = Equipo

    def get_success_url(self):
        sys_code = self.object.system.id
        success_url = reverse_lazy('got:sys-detail', kwargs={'pk': sys_code})
        return success_url


def add_supply_to_equipment(request, code):
    equipo = get_object_or_404(Equipo, code=code)
    if request.method == 'POST':
        form = SuministrosEquipoForm(request.POST)
        if form.is_valid():
            suministro = form.save(commit=False)
            suministro.equipo = equipo
            suministro.save()
            return redirect(reverse('got:sys-detail-view', args=[equipo.system.id, equipo.code]))
    else:
        form = SuministrosEquipoForm()
        items = Item.objects.all()
    return render(request, 'got/equipment_detail.html', {'form': form, 'equipo': equipo, 'items': items})


@login_required
def transferir_equipo(request, equipo_id):
    equipo = get_object_or_404(Equipo, pk=equipo_id)
    if request.method == 'POST':
        form = TransferenciaForm(request.POST)
        if form.is_valid():
            nuevo_sistema = form.cleaned_data['destino']
            observaciones = form.cleaned_data['observaciones']
            
            sistema_origen = equipo.system            
            equipo.system = nuevo_sistema
            equipo.save()

            rutas = Ruta.objects.filter(equipo=equipo)
            for ruta in rutas:
                ruta.system = nuevo_sistema
                ruta.save()
            
            Transferencia.objects.create(
                equipo=equipo,
                responsable=f"{request.user.first_name} {request.user.last_name}",
                origen=sistema_origen,
                destino=nuevo_sistema,
                observaciones=observaciones
            )
            
            return redirect(nuevo_sistema.get_absolute_url())
    else:
        form = TransferenciaForm()

    context = {
        'form': form,
        'equipo': equipo
    }
    return render(request, 'got/transferencia-equipo.html', context)


@login_required
def reportHoursAsset(request, asset_id):

    asset = get_object_or_404(Asset, pk=asset_id)
    today = date.today()
    dates = [today - timedelta(days=x) for x in range(30)]
    equipos_rotativos = Equipo.objects.filter(system__asset=asset, tipo='r')

    if request.method == 'POST':
        form = ReportHoursAsset(request.POST, asset=asset)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.reporter = request.user
            instance.modified_by = request.user
            instance.save()
            return redirect(request.path)
    else:
        form = ReportHoursAsset(asset=asset)

    hours = HistoryHour.objects.filter(component__system__asset=asset)[:30]

    equipos_data = []
    for equipo in equipos_rotativos:
        horas_reportadas = {date: 0 for date in dates}
        for hour in equipo.hours.filter(report_date__range=(dates[-1], today)):
            if hour.report_date in horas_reportadas:
                horas_reportadas[hour.report_date] += hour.hour

        equipos_data.append({
            'equipo': equipo,
            'horas': [horas_reportadas[date] for date in dates]
        })

    context = { 
        'form': form,
        'horas': hours,
        'asset': asset,
        'equipos_data': equipos_data,
        'equipos_rotativos': equipos_rotativos,
        'dates': dates
    }

    return render(request, 'got/hours_asset.html', context)


'FAILURE REPORTS VIEW'
class FailureListView(LoginRequiredMixin, generic.ListView):

    model = FailureReport
    paginate_by = 15
    template_name = 'got/fail/failurereport_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['assets'] = Asset.objects.filter(area='a')
        context['count_proceso'] = self.get_queryset().filter(closed=False, related_ot__isnull=False).count()
        context['count_abierto'] = self.get_queryset().filter(closed=False).count()
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        asset_id = self.request.GET.get('asset_id')
        state = self.request.GET.get('state')

        if asset_id:
            queryset = queryset.filter(equipo__system__asset_id=asset_id)

        if state == 'abierto':
            queryset = queryset.filter(closed=False, related_ot__isnull=True)
        elif state == 'proceso':
            queryset = queryset.filter(closed=False, related_ot__isnull=False)
        elif state == 'cerrado':
            queryset = queryset.filter(closed=True)

        if self.request.user.groups.filter(name='maq_members').exists():
            supervised_assets = Asset.objects.filter(supervisor=self.request.user)
            queryset = queryset.filter(equipo__system__asset__in=supervised_assets)
        elif self.request.user.groups.filter(name='buzos_members').exists():
            supervised_assets = Asset.objects.filter(area='b')
            queryset = queryset.filter(equipo__system__asset__in=supervised_assets)

        return queryset
    

class FailureDetailView(LoginRequiredMixin, generic.DetailView):
    model = FailureReport
    template_name = 'got/fail/failurereport_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        failurereport = self.get_object()
        # Obtener el sistema del equipo del reporte de falla
        system = failurereport.equipo.system
        # Obtener las OTs existentes del sistema
        existing_ots = Ot.objects.filter(system=system)
        context['existing_ots'] = existing_ots
        return context


class FailureReportForm(LoginRequiredMixin, CreateView):
    model = FailureReport
    form_class = failureForm
    template_name = 'got/fail/failurereport_form.html'
    http_method_names = ['get', 'post']

    def send_email(self, context):
        """Sends an email compiled from the given context."""
        subject = 'Nuevo Reporte de Falla'
        email_template_name = 'got/failure_report_email.txt'
        
        email_body_html = render_to_string(email_template_name, context)
        
        email = EmailMessage(
            subject,
            email_body_html,
            settings.EMAIL_HOST_USER,
            [user.email for user in Group.objects.get(name='super_members').user_set.all()],
            reply_to=[settings.EMAIL_HOST_USER]
        )
        
        if self.object.evidence:
            mimetype = f'image/{self.object.evidence.name.split(".")[-1]}'
            email.attach(
                'Evidencia.' + self.object.evidence.name.split(".")[-1],
                self.object.evidence.read(),
                mimetype
            )
        
        email.send()

    def get_email_context(self):
        """Builds the context dictionary for the email."""
        impacts_display = [self.object.get_impact_display(code) for code in self.object.impact]
        return {
            'reporter': self.object.report,
            'moment': self.object.moment.strftime('%Y-%m-%d %H:%M'),
            'equipo': f'{self.object.equipo.system.asset}-{self.object.equipo.name}',
            'description': self.object.description,
            'causas': self.object.causas,
            'suggest_repair': self.object.suggest_repair,
            'impact': impacts_display, 
            'critico': 'Sí' if self.object.critico else 'No',
            'report_url': self.request.build_absolute_uri(self.object.get_absolute_url()),
        }


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset_id = self.kwargs.get('asset_id')
        asset = get_object_or_404(Asset, pk=asset_id)
        context['asset_main'] = asset
        if 'image_form' not in context:
            context['image_form'] = UploadImages()
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        asset_id = self.kwargs.get('asset_id')
        asset = get_object_or_404(Asset, pk=asset_id)
        form.fields['equipo'].queryset = Equipo.objects.filter(system__asset=asset)
        return form
    
    def post(self, request, *args, **kwargs):
        form = self.get_form()
        image_form = UploadImages(request.POST, request.FILES)
        
        if form.is_valid() and image_form.is_valid():
            # Asignar el nombre completo del usuario al campo 'report'
            full_name = request.user.get_full_name()
            if not full_name.strip():
                full_name = request.user.username
            form.instance.report = full_name
            form.instance.modified_by = request.user
            response = super().form_valid(form)
            # context = self.get_email_context()  
            # self.send_email(context)
            for file in request.FILES.getlist('file_field'):
                Image.objects.create(failure=self.object, image=file)
            return response
        else:
            return self.form_invalid(form)
    
    def form_invalid(self, form, **kwargs):
        context = self.get_context_data(form=form, **kwargs)
        return self.render_to_response(context)


class FailureReportUpdate(LoginRequiredMixin, UpdateView):

    model = FailureReport
    form_class = failureForm
    template_name = 'got/fail/failurereport_form.html'
    http_method_names = ['get', 'post']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset = self.get_object().equipo.system.asset
        context['asset_main'] = asset
        # Añadir el formulario de imágenes si es necesario
        if 'image_form' not in context:
            context['image_form'] = UploadImages()
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        asset = self.get_object().equipo.system.asset
        form.fields['equipo'].queryset = Equipo.objects.filter(system__asset=asset)
        return form

    def form_valid(self, form):
        form.instance.modified_by = self.request.user
        # Si el campo 'related_ot' está en el formulario, actualizarlo
        if 'related_ot' in form.cleaned_data:
            form.instance.related_ot = form.cleaned_data['related_ot']
            # Si la OT seleccionada está en estado 'f', marcar el reporte como cerrado
            if form.cleaned_data['related_ot'].state == 'f':
                form.instance.closed = True
            else:
                form.instance.closed = False
        return super().form_valid(form)
    

def fail_pdf(request, pk):
    registro = FailureReport.objects.get(pk=pk)
    context = {'fail': registro}
    return render_to_pdf('got/fail/fail_pdf.html', context)


@permission_required('got.can_see_completely')
def crear_ot_failure_report(request, fail_id):
    fail = get_object_or_404(FailureReport, pk=fail_id)
    nueva_ot = Ot(
        description=f"Reporte de falla - {fail.equipo}",
        state='x',
        supervisor=f"{request.user.first_name} {request.user.last_name}",
        tipo_mtto='c',
        system=fail.equipo.system,
        modified_by=request.user
    )
    nueva_ot.save()

    fail.related_ot = nueva_ot
    fail.save()
    return redirect('got:ot-detail', pk=nueva_ot.pk)


@permission_required('got.can_see_completely')
def asociar_ot_failure_report(request, fail_id):
    if request.method == 'POST':
        ot_id = request.POST.get('ot_id')
        fail = get_object_or_404(FailureReport, pk=fail_id)
        ot = get_object_or_404(Ot, num_ot=ot_id)
        fail.related_ot = ot

        # Verificar el estado de la OT y actualizar el campo 'closed' del reporte de falla
        if ot.state == 'f':
            fail.closed = True
        fail.save()

        return redirect('got:failure-report-detail', pk=fail_id)
    else:
        return redirect('got:failure-report-detail', pk=fail_id)


'OTS VIEWS'
class OtListView(LoginRequiredMixin, generic.ListView):

    model = Ot
    paginate_by = 15

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.user.groups.filter(name='buzos_members').exists():
            info_filter = Asset.objects.filter(area='b')
        else:
            info_filter = Asset.objects.all()
        context['asset'] = info_filter

        super_group = Group.objects.get(name='super_members')
        users_in_group = super_group.user_set.all()
        context['super_members'] = users_in_group

        return context

    def get_queryset(self):
        queryset = Ot.objects.all()
        state = self.request.GET.get('state')
        asset_id = self.request.GET.get('asset_id')
        responsable_id = self.request.GET.get('responsable')

        if self.request.user.groups.filter(name='maq_members').exists():
            supervised_assets = Asset.objects.filter(
                supervisor=self.request.user)
            queryset = queryset.filter(system__asset__in=supervised_assets)
        elif self.request.user.groups.filter(name='buzos_members').exists():
            supervised_assets = Asset.objects.filter(
                area='b')

            queryset = queryset.filter(system__asset__in=supervised_assets)

        if state:
            queryset = queryset.filter(state=state)

        keyword = self.request.GET.get('keyword')
        if keyword:
            queryset = Ot.objects.filter(description__icontains=keyword)
            return queryset

        if asset_id:
            queryset = queryset.filter(system__asset_id=asset_id)
        if responsable_id:
            queryset = queryset.filter(supervisor__icontains=responsable_id)

        return queryset


class OtDetailView(LoginRequiredMixin, generic.DetailView):

    model = Ot
    template_name = 'got/ots/ot_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['state_form'] = FinishOtForm()
        context['image_form'] = UploadImages()

        context['doc_form'] = DocumentForm()

        if self.request.user.groups.filter(name='super_members').exists():
            context['task_form'] = ActForm()
            print('sjgdoasd')
        else:
            # context['task_form'] = ActFormNoSup()
            context['task_form'] = ActForm()

        context['all_tasks_finished'] = not self.get_object().task_set.filter(finished=False).exists()
        context['has_activities'] = self.get_object().task_set.exists()

        failure_report = FailureReport.objects.filter(related_ot=self.get_object())
        context['failure_report'] = failure_report
        context['failure'] = failure_report.exists()

        rutas = self.get_object().ruta_set.all()
        context['rutas'] = rutas
        context['equipos'] = set([ruta.equipo for ruta in rutas])

        system = self.get_object().system
        context['electric_motors'] = system.equipos.filter(Q(tipo='e') | Q(tipo='g'))
        context['has_electric_motors'] = system.equipos.filter(Q(tipo='e') | Q(tipo='g')).exists()
        context['megger_tests'] = Megger.objects.filter(ot=self.get_object())

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        ot = self.get_object()
        
        if 'add-doc' in request.POST:
            doc_form = DocumentForm(request.POST, request.FILES)
            document = doc_form.save(commit=False)
            document.ot = get_object_or_404(Ot, pk=ot.num_ot)
            document.save()
            return redirect(ot.get_absolute_url()) 

        if 'delete_task' in request.POST:
            task_id = request.POST.get('delete_task_id')
            task = Task.objects.get(id=task_id, ot=ot)
            task.modified_by = request.user 
            task.save()
            task.delete()
            return redirect(ot.get_absolute_url()) 
    
        task_form_class = ActForm if request.user.groups.filter(name='super_members').exists() else ActFormNoSup
        task_form = task_form_class(request.POST, request.FILES)
        image_form = UploadImages(request.POST, request.FILES)

        if task_form.is_valid() and image_form.is_valid():
            task = task_form.save(commit=False)
            task.ot = ot
            task.modified_by = request.user 
            task.save()

            for file in request.FILES.getlist('file_field'):
                Image.objects.create(task=task, image=file)

        state_form = FinishOtForm(request.POST)

        if 'finish_ot' in request.POST and state_form.is_valid():
            self.object.state = 'f'
            self.object.modified_by = request.user
            signature_image = request.FILES.get('signature_image', None)
            signature_data = request.POST.get('sign_supervisor', None)

            rutas_relacionadas = Ruta.objects.filter(ot=ot)
            for ruta in rutas_relacionadas:
                actualizar_rutas_dependientes(ruta)

            fallas_relacionadas = FailureReport.objects.filter(related_ot=ot)
            for fail in fallas_relacionadas:
                fail.closed = True
                fail.modified_by = request.user
                fail.save()

            if signature_image:
                self.object.sign_supervision = signature_image
            elif signature_data:
                format, imgstr = signature_data.split(';base64,')
                ext = format.split('/')[-1]
                filename = f'supervisor_signature_{uuid.uuid4()}.{ext}'
                data = ContentFile(base64.b64decode(imgstr), name=filename)
                self.object.sign_supervision.save(filename, data, save=True)
            
            self.object.save()
            return redirect(ot.get_absolute_url())

        elif 'submit_task' in request.POST and task_form.is_valid():
            act = task_form.save(commit=False)
            act.ot = ot
            if isinstance(task_form, ActFormNoSup):
                act.responsible = request.user
            act.modified_by = request.user
            act.save()
            return redirect(ot.get_absolute_url())

        context = {'ot': ot, 'task_form': task_form, 'state_form': state_form}

        return render(request, self.template_name, context)


class OtCreate(CreateView):

    model = Ot
    http_method_names = ['get', 'post']

    def get_form_class(self):
        if self.request.user.groups.filter(name='super_members').exists():
            return OtForm
        else:
            return OtFormNoSup

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        asset_id = self.kwargs.get('pk')
        asset = Asset.objects.get(pk=asset_id)
        kwargs['asset'] = asset
        return kwargs

    def form_valid(self, form):
        ot = form.save(commit=False)
        ot.modified_by = self.request.user
        if isinstance(form, OtFormNoSup):
            ot.supervisor = self.request.user.get_full_name()
        ot.save()
        return redirect('got:ot-detail', pk=ot.pk)


class OtUpdate(UpdateView):

    model = Ot
    http_method_names = ['get', 'post']

    def get_form_class(self):
        if self.request.user.groups.filter(name='super_members').exists():
            return OtForm
        else:
            return OtFormNoSup

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        ot_instance = self.get_object()
        kwargs['asset'] = ot_instance.system.asset
        return kwargs

    def form_valid(self, form):
        ot = form.save(commit=False)
        ot.modified_by = self.request.user  # Asignar el usuario que modifica
        ot.save()
        return super().form_valid(form)


class OtDelete(DeleteView):

    model = Ot
    success_url = reverse_lazy('got:ot-list')



def ot_pdf(request, num_ot):

    ot_info = Ot.objects.get(num_ot=num_ot)
    fallas = FailureReport.objects.filter(related_ot=ot_info)

    try:
        fallas = FailureReport.objects.filter(related_ot=ot_info)
        failure = True
    except FailureReport.DoesNotExist:
        fallas = None
        failure = False

    context = {'ot': ot_info, 'fallas': fallas, 'failure': failure}
    template_path = 'got/pdf_template.html'
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="orden_de_trabajo_{num_ot}.pdf"'
    
    template = get_template(template_path)
    html = template.render(context)
    
    # Crear el PDF y enviarlo directamente a la respuesta HTTP
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response


'TASKS VIEW'
class AssignedTaskByUserListView(LoginRequiredMixin, generic.ListView):

    model = Task
    template_name = 'got/task/assignedtasks_list_pendient.html'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.groups.filter(name='buzos_members').exists():
            context['assets'] = Asset.objects.filter(area='b')
        else:
            context['assets'] = Asset.objects.all()
        context['all_users'] = operational_users(self.request.user)
        context['total_tasks'] = self.get_queryset().count()
        return context

    def get_queryset(self):
        queryset = Task.objects.filter(ot__isnull=False, start_date__isnull=False, finished=False).order_by('start_date')
        current_user = self.request.user

        asset_id = self.request.GET.get('asset_id')
        if asset_id:
            queryset = queryset.filter(ot__system__asset_id=asset_id)
        responsable_id = self.request.GET.get('worker')
        if responsable_id:
            queryset = queryset.filter(responsible=responsable_id)

        if current_user.groups.filter(name='serport_members').exists():
            return queryset.filter(responsible=current_user)
        elif current_user.groups.filter(name='super_members').exists():
            return queryset
        elif current_user.groups.filter(name='maq_members').exists():
            return queryset.filter(ot__system__asset__supervisor=current_user)
        elif current_user.groups.filter(name='buzos_members').exists():
            user_station = self.request.user.profile.station
            if user_station:
                return queryset.filter(ot__system__asset__area='b', ot__system__location__in=user_station)
            return queryset.filter(ot__system__asset__area='b')
        
        return queryset.none() 


class TaskDetailView(LoginRequiredMixin, generic.DetailView):

    model = Task


class TaskCreate(CreateView):

    model = Task
    http_method_names = ['get', 'post']
    form_class = RutActForm

    def form_valid(self, form):
        pk = self.kwargs['pk']
        ruta = get_object_or_404(Ruta, pk=pk)

        form.instance.ruta = ruta
        form.instance.finished = False
        form.instance.modified_by = self.request.user

        return super().form_valid(form)

    def get_success_url(self):
        task = self.object
        return reverse('got:sys-detail', args=[task.ruta.system.id])


class TaskUpdate(UpdateView):

    model = Task
    template_name = 'got/task_form.html'
    form_class = ActForm
    second_form_class = UploadImages

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'image_form' not in context:
            context['image_form'] = self.second_form_class()
        context['images'] = Image.objects.filter(task=self.get_object())
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        image_form = self.second_form_class(request.POST, request.FILES)
        if form.is_valid() and image_form.is_valid():
            response = super().form_valid(form)
            if form.cleaned_data.get('delete_images'):
                self.object.images.all().delete()
            for img in request.FILES.getlist('file_field'):
                Image.objects.create(task=self.object, image=img)
            return response
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        form.instance.modified_by = self.request.user
        return super().form_valid(form)

    def form_invalid(self, form, **kwargs):
        return self.render_to_response(self.get_context_data(form=form, **kwargs))
    

class TaskDelete(DeleteView):

    model = Task
    success_url = reverse_lazy('got:ot-list')


class TaskUpdaterut(UpdateView):

    model = Task
    form_class = RutActForm
    template_name = 'got/task_form.html'
    http_method_names = ['get', 'post']

    def form_valid(self, form):
        form.instance.modified_by = self.request.user  # Asignar el usuario que modifica la tarea
        return super().form_valid(form)

    def get_success_url(self):
        sys_id = self.object.ruta.system.id
        return reverse_lazy('got:sys-detail', kwargs={'pk': sys_id})
    

class TaskDeleterut(DeleteView):

    model = Task

    def get_success_url(self):
        sys_id = self.object.ruta.system.id
        return reverse_lazy('got:sys-detail', kwargs={'pk': sys_id})

    def get(self, request, *args, **kwargs):
        context = {'task': self.get_object()}
        return render(request, 'got/task_confirm_delete.html', context)


class Finish_task(UpdateView):

    model = Task
    form_class = FinishTask
    template_name = 'got/task_finish_form.html'
    second_form_class = UploadImages
    success_url = reverse_lazy('got:my-tasks')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'image_form' not in context:
            context['image_form'] = self.second_form_class()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        image_form = self.second_form_class(request.POST, request.FILES)
        if form.is_valid() and image_form.is_valid():
            response = super().form_valid(form)
            for img in request.FILES.getlist('file_field'):
                Image.objects.create(task=self.object, image=img)
            return response
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        form.instance.modified_by = self.request.user  # Asignar el usuario actual
        return super().form_valid(form)

    def form_invalid(self, form, **kwargs):
        return self.render_to_response(self.get_context_data(form=form, **kwargs))
    

class Finish_task_ot(UpdateView):

    model = Task
    form_class = FinishTask
    template_name = 'got/task_finish_form.html'
    second_form_class = UploadImages

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'image_form' not in context:
            context['image_form'] = self.second_form_class()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        image_form = self.second_form_class(request.POST, request.FILES)
        if form.is_valid() and image_form.is_valid():
            return self.form_valid(form, image_form)

        else:
            return self.form_invalid(form)

    def form_valid(self, form, image_form):
        form.instance.modified_by = self.request.user 
        self.object = form.save()

        for img in self.request.FILES.getlist('file_field'):
            Image.objects.create(task=self.object, image=img)

        ot = self.object.ot
        success_url = reverse('got:ot-detail', kwargs={'pk': ot.pk})
        return HttpResponseRedirect(success_url)

    def form_invalid(self, form, **kwargs):
        return self.render_to_response(self.get_context_data(form=form, **kwargs))


class Reschedule_task(UpdateView):

    model = Task
    form_class = RescheduleTaskForm
    template_name = 'got/task/task_reschedule.html'
    success_url = reverse_lazy('got:my-tasks')

    def form_valid(self, form):
        form.instance.modified_by = self.request.user
        return super().form_valid(form)
    

'RUTINAS VIEWS'
@login_required
def RutaListView(request):

    suministro_prefetch = Prefetch('suministros', queryset=Suministro.objects.all(), to_attr='all_suministros')
    equipo_prefetch = Prefetch('equipos', queryset=Equipo.objects.prefetch_related(suministro_prefetch).annotate(num_suministros=Count('suministros')).filter(num_suministros__gt=0), to_attr='all_equipos')
    system_prefetch = Prefetch('system_set', queryset=System.objects.prefetch_related(equipo_prefetch).annotate(num_equipos_with_suministros=Count('equipos__suministros')).filter(num_equipos_with_suministros__gt=0), to_attr='all_systems')
    assets = Asset.objects.filter(area='a').prefetch_related(system_prefetch).annotate(num_systems_with_equipos=Count('system__equipos__suministros')).filter(num_systems_with_equipos__gt=0)

    diques = Ruta.objects.filter(name__icontains='DIQUE')
    barcos = Asset.objects.filter(area='a')


    motores_data = []
    for barco in barcos:
        sistema = barco.system_set.filter(group=200).first()
        sistema2 = barco.system_set.filter(group=300).first()
        motores_info = {
            'name': barco.name,
            'estribor': {
                'marca': '---',
                'modelo': '---',
                'lubricante': '---',
                'capacidad': 0,
                'fecha': '---',
                },
            'babor': {
                'marca': '---',
                'modelo': '---'},
            'generador': {'marca': '---', 'modelo': '---', 'lubricante': '---', 'capacidad': 0}
        }

        if sistema:
            motor_estribor = sistema.equipos.filter(name__icontains='Motor propulsor estribor').first()
            motor_babor = sistema.equipos.filter(name__icontains='Motor propulsor babor').first()
            motor_generador1 = sistema2.equipos.filter(Q(name__icontains='Motor generador estribor') | Q(name__icontains='Motor generador 1')).first() if sistema2 else None
            motor_generador2 = sistema2.equipos.filter(Q(name__icontains='Motor generador babor') | Q(name__icontains='Motor generador 2')).first() if sistema2 else None
            
            if motor_estribor:
                motores_info['estribor'] = {
                    'marca': motor_estribor.marca,
                    'modelo': motor_estribor.model,
                    'lubricante': motor_estribor.lubricante,
                    'capacidad': motor_estribor.volumen,
                    'horometro': motor_estribor.horometro,
                    'fecha': motor_estribor.last_hour_report_date(),
                    }
            if motor_babor:
                motores_info['babor'] = {
                    'marca': motor_babor.marca,
                    'modelo': motor_babor.model,
                    'lubricante': motor_babor.lubricante,
                    'capacidad': motor_babor.volumen,
                    'horometro': motor_babor.horometro,
                    'fecha': motor_babor.last_hour_report_date()
                    }
            if motor_generador1:
                motores_info['generador1'] = {
                    'marca': motor_generador1.marca,
                    'modelo': motor_generador1.model,
                    'lubricante': motor_generador1.lubricante,
                    'capacidad': motor_generador1.volumen,
                    'horometro': motor_generador1.horometro,
                    'fecha': motor_generador1.last_hour_report_date()
                    }
            if motor_generador2:
                motores_info['generador2'] = {
                    'marca': motor_generador2.marca,
                    'modelo': motor_generador2.model,
                    'lubricante': motor_generador2.lubricante,
                    'capacidad': motor_generador2.volumen,
                    'horometro': motor_generador2.horometro,
                    'fecha': motor_generador2.last_hour_report_date()
                    }

        motores_data.append(motores_info)

    context = {
        'assets': assets,
        'dique_rutinas': diques,
        'barcos': barcos,
        'motores_data': motores_data,
    }
    return render(request, 'got/ruta_list.html', context)


class RutaCreate(CreateView):

    model = Ruta
    form_class = RutaForm

    def form_valid(self, form):
        pk = self.kwargs['pk']
        system = get_object_or_404(System, pk=pk)

        form.instance.system = system
        form.instance.modified_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        ruta = self.object
        return reverse('got:sys-detail', args=[ruta.system.id])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['system'] = System.objects.get(pk=self.kwargs['pk'])
        return kwargs


class RutaUpdate(UpdateView):

    model = Ruta
    form_class = RutaForm

    def form_valid(self, form):
        form.instance.modified_by = self.request.user  # Asignar el usuario actual al campo modified_by
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['system'] = self.object.system
        return kwargs


class RutaDelete(DeleteView):

    model = Ruta

    def get_success_url(self):
        sys_code = self.object.system.id
        success_url = reverse_lazy('got:sys-detail', kwargs={'pk': sys_code})
        return success_url


@login_required
def crear_ot_desde_ruta(request, ruta_id):
    ruta = get_object_or_404(Ruta, pk=ruta_id)

    if request.method == 'POST':
        asociar_otros = request.POST.get('asociar_otros', 'off') == 'on'
        rutinas_seleccionadas_ids = [str(ruta_id)]
        if asociar_otros:
            # Obtener rutinas seleccionadas
            rutinas_seleccionadas_ids += request.POST.getlist('rutinas_seleccionadas')

        rutinas_seleccionadas = Ruta.objects.filter(pk__in=rutinas_seleccionadas_ids)
        num_rutinas = rutinas_seleccionadas.count()

        primera_ruta = rutinas_seleccionadas.first()
        nueva_ot = Ot(
            description=f"Rutina de mantenimiento con código {primera_ruta.name}",
            state='x',
            supervisor=f"{request.user.first_name} {request.user.last_name}",
            tipo_mtto='p',
            system=primera_ruta.system,
            modified_by=request.user 
        )
        nueva_ot.save()

        def copiar_tasks_y_actualizar_ot(ruta, ot, modify_description=False):
            for task in ruta.task_set.all():
                if modify_description:
                    equipo_sistema = ruta.equipo.name if ruta.equipo else ruta.system.name
                    description = f"{task.description} ({equipo_sistema})"
                else:
                    description = task.description
                Task.objects.create(
                    ot=ot,
                    responsible=task.responsible,
                    description=description,
                    procedimiento=task.procedimiento,
                    hse=task.hse,
                    evidence=task.evidence,
                    start_date=timezone.now().date(),
                    men_time=1,
                    finished=False,
                    modified_by=request.user 
                )

            ruta.ot = ot
            ruta.save()

            if ruta.dependencia:
                copiar_tasks_y_actualizar_ot(ruta.dependencia, ot)

        modify_description = num_rutinas > 1
        for selected_ruta in rutinas_seleccionadas:
            copiar_tasks_y_actualizar_ot(selected_ruta, nueva_ot, modify_description)

        # copiar_tasks_y_actualizar_ot(ruta, nueva_ot)
        return redirect('got:ot-detail', pk=nueva_ot.pk)
    else:
        # Manejar solicitudes GET para crear una OT para una sola rutina
        nueva_ot = Ot(
            description=f"Rutina de mantenimiento con código {ruta.name}",
            state='x',
            supervisor=f"{request.user.first_name} {request.user.last_name}",
            tipo_mtto='p',
            system=ruta.system,
            modified_by=request.user 
        )
        nueva_ot.save()

        def copiar_tasks_y_actualizar_ot(ruta, ot):
            for task in ruta.task_set.all():
                Task.objects.create(
                    ot=ot,
                    responsible=task.responsible,
                    description=task.description,
                    procedimiento=task.procedimiento,
                    hse=task.hse,
                    evidence=task.evidence,
                    start_date=timezone.now().date(),
                    men_time=1,
                    finished=False,
                    modified_by=request.user 
                )

            ruta.ot = ot
            ruta.save()

            if ruta.dependencia:
                copiar_tasks_y_actualizar_ot(ruta.dependencia, ot)

        copiar_tasks_y_actualizar_ot(ruta, nueva_ot)

        return redirect('got:ot-detail', pk=nueva_ot.pk)


def rutina_form_view(request, ruta_id):
    ruta = get_object_or_404(Ruta, code=ruta_id)

    tasks_ruta_principal = Task.objects.filter(ruta=ruta)
    fecha_actual = timezone.now().date()
    fecha_seleccionada = request.POST.get('fecha', fecha_actual)
    ot_state = 'f' 

    def procesar_tasks_y_dependencias(ruta, formset_data):
        tasks = Task.objects.filter(ruta=ruta)
        for task in tasks:
            realizado = request.POST.get(f'realizado_{task.id}') == 'on'
            observaciones = request.POST.get(f'observaciones_{task.id}')
            evidencias = request.FILES.getlist(f'evidencias_{task.id}')
            
            if not realizado:
                ot_state = 'x'  # Si alguna tarea no está realizada, la OT no estará finalizada
            
            formset_data.append({
                'task': task,
                'realizado': realizado,
                'observaciones': observaciones,
                'evidencias': evidencias
            })

        
        if ruta.dependencia:
            procesar_tasks_y_dependencias(ruta.dependencia, formset_data)


    if request.method == 'POST':
        formset_data = []
        procesar_tasks_y_dependencias(ruta, formset_data)

        signature_image = request.FILES.get('signature_image')
        signature_data = request.POST.get('signature')
        signature_file = None
        if signature_image:
            signature_file = signature_image
        if signature_data:
            format, imgstr = signature_data.split(';base64,')
            ext = format.split('/')[-1]
            filename = f'signature_{uuid.uuid4()}.{ext}'
            signature_file = ContentFile(base64.b64decode(imgstr), name=filename)

        new_ot = Ot.objects.create(
            system=ruta.system,
            description=f"Rutina de mantenimiento con código {ruta.name}",
            supervisor=request.user.get_full_name(),
            state=ot_state,
            tipo_mtto='p',
            sign_supervision=signature_file,
            modified_by=request.user
        )
            
        for form_data in formset_data:
            new_task = Task.objects.create(
                ot=new_ot,
                description=form_data['task'].description,
                responsible=request.user,
                news=form_data['observaciones'],
                finished=form_data['realizado'],
                start_date=fecha_seleccionada,
                modified_by=request.user
            )
            # Guardar evidencias si las hay
            for evidencia in form_data['evidencias']:
                Image.objects.create(task=new_task, image=evidencia)

        def actualizar_ruta_y_dependencias(ruta, ot, fecha):
            ruta.intervention_date = fecha
            ruta.ot = ot
            ruta.save()
            if ruta.dependencia:
                actualizar_ruta_y_dependencias(ruta.dependencia, ot, fecha)
        actualizar_ruta_y_dependencias(ruta, new_ot, fecha_seleccionada)


        print("Nueva OT creada con éxito:", new_ot)
        return redirect(reverse('got:sys-detail', args=[ruta.system.id]))

    else:
        formset_data = [{'task': task, 'form': ActivityForm(), 'upload_form': UploadImages()} for task in tasks_ruta_principal]
        dependencias = []
        
        # Agregar las tareas de las rutas dependientes
        print(f'Hola{ruta.dependencia}')
        if ruta.dependencia:
            dependencias = [ruta.dependencia]
            while dependencias[-1].dependencia:
                dependencias.append(dependencias[-1].dependencia)

            for dependencia in dependencias:
                tasks_dependencia = Task.objects.filter(ruta=dependencia)
                formset_data += [{'task': task, 'form': ActivityForm(), 'upload_form': UploadImages(), 'dependencia': dependencia.name} for task in tasks_dependencia]

    return render(request, 'got/ruta_ot_form.html', 
                  {'formset_data': formset_data, 'ruta': ruta, 'dependencias': dependencias, 'fecha_seleccionada': fecha_seleccionada}
                  )



def buceomtto(request):

    location_filter = request.GET.get('location', None)
    buceo = Asset.objects.filter(area='b')

    buceo_rowspan = len(buceo) + 1
    total_oks = 0
    total_non_dashes = 0

    buceo_data = []
    for asset in buceo:
        mensual = asset.check_ruta_status(30, location_filter)
        trimestral = asset.check_ruta_status(90, location_filter)
        semestral = asset.check_ruta_status(180, location_filter)
        anual = asset.check_ruta_status(365, location_filter)
        bianual = asset.check_ruta_status(730, location_filter)

        for status in [mensual, trimestral, semestral, anual, bianual]:
            if status == "Ok":
                total_oks += 1
            if status != "---":
                total_non_dashes += 1

        buceo_data.append({
            'asset': asset,
            'mensual': mensual,
            'trimestral': trimestral,
            'semestral': semestral,
            'anual': anual,
            'bianual': bianual,
            'buceo': buceo_data,
        })
    
    ind_mtto = round((total_oks*100)/total_non_dashes, 2)

    context = {
        'buceo': buceo_data,
        'ind_mtto': ind_mtto,
        'buceo_rowspan': buceo_rowspan,
    }
    return render(request, 'got/buceomtto.html', context)


'OPERATIONS VIEW'
# def OperationListView(request):
#     assets = Asset.objects.filter(area='a')
#     operaciones_list = Operation.objects.order_by('start').prefetch_related(
#         Prefetch(
#             'requirement_set',
#             queryset=Requirement.objects.order_by('responsable').prefetch_related('images')
#         )
#     )

#     page = request.GET.get('page', 1)
#     paginator = Paginator(operaciones_list, 10)  # Mostrar 10 operaciones por página

#     try:
#         operaciones = paginator.page(page)
#     except PageNotAnInteger:
#         operaciones = paginator.page(1)
#     except EmptyPage:
#         operaciones = paginator.page(paginator.num_pages)

#     operations_data = []
#     for asset in assets:
#         asset_operations = asset.operation_set.all().values(
#             'start', 'end', 'proyecto', 'requirements', 'confirmado'
#         )
#         operations_data.append({
#             'asset': asset,
#             'operations': list(asset_operations)
#         })

#     form = OperationForm(request.POST or None)
#     modal_open = False 

#     if request.method == 'POST':
#         form = OperationForm(request.POST)
#         if form.is_valid():
#             form.save()
#             return redirect(request.path)
#         else:
#             modal_open = True 
#     else:
#         form = OperationForm()

#     context= {
#         'operations_data': operations_data,
#         'operation_form': form,
#         'modal_open': modal_open,
#         'operaciones': operaciones,
#         'requirement_form': RequirementForm(),
#         'upload_images_form': UploadImages(),
#     }

#     return render(request, 'got/operations/operation_list.html', context)

def OperationListView(request):
    assets = Asset.objects.filter(area='a')

    today = timezone.now().date()
    show_past = request.GET.get('show_past', 'false').lower() == 'true'

    # Filtrar operaciones para la tabla
    if show_past:
        operaciones_list = Operation.objects.order_by('start').prefetch_related(
            Prefetch(
                'requirement_set',
                queryset=Requirement.objects.order_by('responsable').prefetch_related('images')
            )
        )
    else:
        operaciones_list = Operation.objects.filter(end__gte=today).order_by('start').prefetch_related(
            Prefetch(
                'requirement_set',
                queryset=Requirement.objects.order_by('responsable').prefetch_related('images')
            )
        )

    # Paginación
    page = request.GET.get('page', 1)
    paginator = Paginator(operaciones_list, 10)  # Mostrar 10 operaciones por página

    try:
        operaciones = paginator.page(page)
    except PageNotAnInteger:
        operaciones = paginator.page(1)
    except EmptyPage:
        operaciones = paginator.page(paginator.num_pages)

    # Datos para el gráfico: incluir todas las operaciones
    operations_data = []
    for asset in assets:
        asset_operations = asset.operation_set.all().values(
            'start', 'end', 'proyecto', 'requirements', 'confirmado'
        )
        operations_data.append({
            'asset': asset,
            'operations': list(asset_operations)
        })

    form = OperationForm(request.POST or None)
    modal_open = False 

    if request.method == 'POST':
        form = OperationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(request.path)
        else:
            modal_open = True 
    else:
        form = OperationForm()

    context = {
        'operations_data': operations_data,
        'operation_form': form,
        'modal_open': modal_open,
        'operaciones': operaciones,
        'requirement_form': RequirementForm(),
        'upload_images_form': UploadImages(),
        'show_past': show_past,
    }

    return render(request, 'got/operations/operation_list.html', context)


class OperationUpdate(UpdateView):

    model = Operation
    form_class = OperationForm
    template_name = 'got/operations/operation_form.html'

    def get_success_url(self):

        return reverse('got:operation-list')


class OperationDelete(DeleteView):

    model = Operation
    success_url = reverse_lazy('got:operation-list')


@permission_required('got.can_create_requirement', raise_exception=True)
def requirement_create(request, operation_id):
    operation = get_object_or_404(Operation, id=operation_id)
    if request.method == 'POST':
        requirement_form = RequirementForm(request.POST)
        upload_images_form = UploadImages(request.POST, request.FILES)
        if requirement_form.is_valid() and upload_images_form.is_valid():
            requirement = requirement_form.save(commit=False)
            requirement.operation = operation
            requirement.save()
            # Acceder directamente a los archivos desde request.FILES
            for f in request.FILES.getlist('file_field'):
                Image.objects.create(image=f, requirements=requirement)
            return redirect('got:operation-list')
    else:
        requirement_form = RequirementForm()
        upload_images_form = UploadImages()
    context = {
        'requirement_form': requirement_form,
        'upload_images_form': upload_images_form,
        'operation': operation,
    }
    return render(request, 'got/operations/requirement_form.html', context)


def requirement_update(request, pk):
    requirement = get_object_or_404(Requirement, pk=pk)
    if request.user.has_perm('got.can_create_requirement'):
        RequirementFormClass = FullRequirementForm
        can_delete_images = True
    else:
        RequirementFormClass = LimitedRequirementForm
        can_delete_images = False

    if request.method == 'POST':
        requirement_form = RequirementFormClass(request.POST, instance=requirement)
        upload_images_form = UploadImages(request.POST, request.FILES)
        if requirement_form.is_valid() and upload_images_form.is_valid():
            requirement_form.save()
            # Manejar eliminación de imágenes
            if can_delete_images:
                images_to_delete = request.POST.getlist('delete_images')
                Image.objects.filter(id__in=images_to_delete).delete()
            # Guardar nuevas imágenes
            for f in request.FILES.getlist('file_field'):
                Image.objects.create(image=f, requirements=requirement)
            return redirect('got:operation-list')
    else:
        requirement_form = RequirementFormClass(instance=requirement)
        upload_images_form = UploadImages()
    context = {
        'requirement_form': requirement_form,
        'upload_images_form': upload_images_form,
        'requirement': requirement,
        'can_delete_images': can_delete_images,
    }
    return render(request, 'got/operations/requirement_form.html', context)


def requirement_delete(request, pk):
    requirement = get_object_or_404(Requirement, pk=pk)
    if request.method == 'POST':
        requirement.delete()
        return redirect('got:operation-list')
    return render(request, 'got/operations/requirement_confirm_delete.html', {'requirement': requirement})


'MEGGERS VIEW'
def megger_view(request, pk):
    megger = get_object_or_404(Megger, pk=pk) 
    estator = get_object_or_404(Estator, megger=megger)
    excitatriz = get_object_or_404(Excitatriz, megger=megger)
    rotormain = get_object_or_404(RotorMain, megger=megger)
    rotoraux = get_object_or_404(RotorAux, megger=megger)
    rodamientosescudos = get_object_or_404(RodamientosEscudos, megger=megger)

    estator_form = EstatorForm(request.POST or None, instance=estator)
    excitatriz_form = ExcitatrizForm(request.POST or None, instance=excitatriz)
    rotormain_form = RotorMainForm(request.POST or None, instance=rotormain)
    rotoraux_form = RotorAuxForm(request.POST or None, instance=rotoraux)
    rodamientosescudos_form = RodamientosEscudosForm(request.POST or None, instance=rodamientosescudos)

    if request.method == 'POST':
        estator_form = EstatorForm(request.POST, instance=estator)
        excitatriz_form = ExcitatrizForm(request.POST, instance=excitatriz)
        rotormain_form = RotorMainForm(request.POST, instance=rotormain)
        rotoraux_form = RotorAuxForm(request.POST, instance=rotoraux)
        rodamientosescudos_form = RodamientosEscudosForm(request.POST, instance=rodamientosescudos)

        if 'submit_estator' in request.POST:
            if estator_form.is_valid():
                estator_form.save()
                return redirect('got:meg-detail', pk=megger.pk)
        elif 'submit_excitatriz' in request.POST:
            if excitatriz_form.is_valid():
                excitatriz_form.save()
                return redirect('got:meg-detail', pk=megger.pk)
        elif 'submit_rotormain' in request.POST:
            if rotormain_form.is_valid():
                rotormain_form.save()
                return redirect('got:meg-detail', pk=megger.pk)
        elif 'submit_rotoraux' in request.POST:
            if rotoraux_form.is_valid():
                rotoraux_form.save()
                return redirect('got:meg-detail', pk=megger.pk)
        elif 'submit_rodamientosescudos' in request.POST:
            if rodamientosescudos_form.is_valid():
                rodamientosescudos_form.save()
                return redirect('got:meg-detail', pk=megger.pk)

    context = {
        'megger': megger,
        'estator_form': estator_form,
        'excitatriz_form': excitatriz_form,
        'rotormain_form': rotormain_form,
        'rotoraux_form': rotoraux_form,
        'rodamientosescudos_form': rodamientosescudos_form,
    }
    return render(request, 'got/meg/megger_form.html', context)


def create_megger(request, ot_id):
    if request.method == 'POST':
        ot = get_object_or_404(Ot, num_ot=ot_id)
        equipo_id = request.POST.get('equipo')
        equipo = get_object_or_404(Equipo, code=equipo_id)

        megger = Megger.objects.create(ot=ot, equipo=equipo)

        Estator.objects.create(megger=megger)
        Excitatriz.objects.create(megger=megger)
        RotorMain.objects.create(megger=megger)
        RotorAux.objects.create(megger=megger)
        RodamientosEscudos.objects.create(megger=megger)

        return redirect('got:meg-detail', pk=megger.pk)
    

def megger_pdf(request, pk):
    registro = Megger.objects.get(pk=pk)
    context = {'meg': registro}
    return render_to_pdf('got/meg/meg_detail.html', context)


'PREOPERACIONAL VIEW'
class SalidaListView(LoginRequiredMixin, generic.ListView):
    model = Preoperacional
    paginate_by = 15
    template_name = 'got/preoperacional/salida_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener la fecha actual
        fecha_actual = timezone.now()

        # Generar rangos de meses y años
        meses = [(i, _(calendar.month_name[i])) for i in range(1, 13)]  # De enero a diciembre
        anios = range(fecha_actual.year - 5, fecha_actual.year + 1)  # Últimos 5 años hasta el actual

        # Pasar estos valores al contexto
        context['fecha_actual'] = fecha_actual
        context['meses'] = meses
        context['anios'] = anios

        return context

class SalidaDetailView(LoginRequiredMixin, generic.DetailView):

    model = Preoperacional
    template_name = 'got/preoperacional/salida_detail.html'


def export_preoperacional_to_excel(request):
    # Obtener el mes y año del request
    mes = int(request.GET.get('mes', datetime.now().month))
    anio = int(request.GET.get('anio', datetime.now().year))

    # Filtrar los registros por el mes y año seleccionados
    preoperacionales = Preoperacional.objects.filter(fecha__month=mes, fecha__year=anio)

    # Crear un archivo de Excel
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = f"Preoperacional {mes}-{anio}"

    # Escribir el encabezado
    headers = [
        'Fecha', 'Vehiculo', 'Responsable', 'Kilometraje', 'Salida', 'Destino', 
        'Autorizado', 'Horas trabajo', 'Medicamentos', 'Molestias', 'Enfermo', 
        'Condiciones', 'Agua', 'Dormido', 'Control', 'Sueño', 'Radio Aire', 
        'Observaciones'
    ]
    for col_num, header in enumerate(headers, 1):
        sheet.cell(row=1, column=col_num).value = header

    # Escribir los datos
    for row_num, preop in enumerate(preoperacionales, 2):
        sheet.cell(row=row_num, column=1).value = preop.fecha.strftime('%d/%m/%Y')
        sheet.cell(row=row_num, column=2).value = str(preop.vehiculo)
        sheet.cell(row=row_num, column=3).value = f"{preop.reporter.first_name} {preop.reporter.last_name}" if preop.reporter else preop.nombre_no_registrado
        sheet.cell(row=row_num, column=4).value = preop.kilometraje
        sheet.cell(row=row_num, column=5).value = preop.salida
        sheet.cell(row=row_num, column=6).value = preop.destino
        sheet.cell(row=row_num, column=7).value = preop.get_autorizado_display()
        sheet.cell(row=row_num, column=8).value = 'Sí' if preop.horas_trabajo else 'No'
        sheet.cell(row=row_num, column=9).value = 'Sí' if preop.medicamentos else 'No'
        sheet.cell(row=row_num, column=10).value = 'Sí' if preop.molestias else 'No'
        sheet.cell(row=row_num, column=11).value = 'Sí' if preop.enfermo else 'No'
        sheet.cell(row=row_num, column=12).value = 'Sí' if preop.condiciones else 'No'
        sheet.cell(row=row_num, column=13).value = 'Sí' if preop.agua else 'No'
        sheet.cell(row=row_num, column=14).value = 'Sí' if preop.dormido else 'No'
        sheet.cell(row=row_num, column=15).value = 'Sí' if preop.control else 'No'
        sheet.cell(row=row_num, column=16).value = 'Sí' if preop.sueño else 'No'
        sheet.cell(row=row_num, column=17).value = 'Sí' if preop.radio_aire else 'No'
        sheet.cell(row=row_num, column=18).value = preop.observaciones

    # Preparar el archivo para la descarga
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=Preoperacional_{mes}-{anio}.xlsx'
    workbook.save(response)
    
    return response


def preoperacional_especifico_view(request, code):
    
    equipo = get_object_or_404(Equipo, code=code)
    rutas_vencidas = [ruta for ruta in equipo.equipos.all() if ruta.next_date < date.today()]

    if request.method == 'POST':
        form = PreoperacionalEspecificoForm(request.POST, equipo_code=equipo.code, user=request.user)
        image_form = UploadImages(request.POST, request.FILES)
        if form.is_valid() and image_form.is_valid():
            preop = form.save(commit=False)
            preop.reporter = request.user if request.user.is_authenticated else None
            preop.vehiculo = equipo
            nuevo_kilometraje = form.cleaned_data['nuevo_kilometraje']
            preop.kilometraje = nuevo_kilometraje
            preop.save()

            horometro_actual = equipo.initial_hours + (equipo.hours.filter(report_date__lt=localdate()).aggregate(total=Sum('hour'))['total'] or 0)
            kilometraje_reportado = nuevo_kilometraje - horometro_actual

            history_hour, created = HistoryHour.objects.get_or_create(
                component=equipo,
                report_date=localdate(),
                defaults={'hour': kilometraje_reportado}
            )

            if not created:
                history_hour.hour = kilometraje_reportado
                history_hour.save()

            equipo.horometro = nuevo_kilometraje
            equipo.save()

            for file in request.FILES.getlist('file_field'):
                Image.objects.create(preoperacional=preop, image=file)

            return redirect('got:gracias', code=equipo.code)
    else:
        form = PreoperacionalEspecificoForm(equipo_code=equipo.code, user=request.user)
        image_form = UploadImages()

    return render(request, 'got/preoperacional/preoperacionalform.html', {'vehiculo': equipo, 'form': form, 'image_form': image_form, 'rutas_vencidas': rutas_vencidas})


'PREOPERACIONAL DIARIO VIEW'
class PreoperacionalListView(LoginRequiredMixin, generic.ListView):
    model = PreoperacionalDiario
    paginate_by = 15
    template_name = 'got/preoperacional/preoperacional_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener la fecha actual
        fecha_actual = timezone.now()

        # Generar rangos de meses y años
        meses = [(i, _(calendar.month_name[i])) for i in range(1, 13)]  # De enero a diciembre
        anios = range(fecha_actual.year - 5, fecha_actual.year + 1)  # Últimos 5 años hasta el actual

        # Pasar estos valores al contexto
        context['fecha_actual'] = fecha_actual
        context['meses'] = meses
        context['anios'] = anios

        return context


class PreoperacionalDetailView(LoginRequiredMixin, generic.DetailView):

    model = PreoperacionalDiario
    template_name = 'got/preoperacional/preoperacional_detail.html'


def preoperacional_diario_view(request, code):
    
    equipo = get_object_or_404(Equipo, code=code)
    rutas_vencidas = [ruta for ruta in equipo.equipos.all() if ruta.next_date < date.today()]

    existente = PreoperacionalDiario.objects.filter(vehiculo=equipo, fecha=localdate()).first()

    if existente:
        mensaje = f"El preoperacional del vehículo {equipo} de la fecha actual ya fue diligenciado y exitosamente enviado. El resultado fue: {'Aprobado' if existente.aprobado else 'No aprobado'}."
        messages.error(request, mensaje)
        return render(request, 'got/preoperacional/preoperacional_restricted.html', {'mensaje': mensaje})
    
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

    return render(request, 'got/preoperacional/preoperacionalform.html', {'vehiculo': equipo, 'form': form, 'image_form': image_form, 'rutas_vencidas': rutas_vencidas, 'pre': True})


def export_preoperacionaldiario_excel(request):
    mes = request.GET.get('mes', timezone.now().month)
    anio = request.GET.get('anio', timezone.now().year)

    # Filtrar los registros por el mes y el año seleccionados
    preoperacional_diarios = PreoperacionalDiario.objects.filter(
        fecha__year=anio,
        fecha__month=mes
    )

    # Crear el libro de Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Preoperacional Diario {mes}-{anio}"
    headers = [
        'Fecha', 'Vehículo', 'Responsable', 'Kilometraje', 'Nivel de Combustible',
        'Nivel de Aceite', 'Nivel de Refrigerante', 'Nivel de Hidráulico', 'Nivel de Líquido de Frenos',
        'Poleas', 'Correas', 'Mangueras', 'Acoples', 'Tanques', 'Radiador', 'Terminales', 'Bujes', 'Rótulas', 
        'Ejes', 'Cruceta', 'Puertas', 'Chapas', 'Manijas', 'Elevavidrios', 'Lunas', 'Espejos', 
        'Vidrio Panorámico', 'Asiento', 'Apoyacabezas', 'Cinturón', 'Aire', 'Caja de Cambios', 
        'Dirección', 'Batería', 'Luces Altas', 'Luces Medias', 'Luces Direccionales', 'Cocuyos', 'Luz de Placa',
        'Luz Interna', 'Pito', 'Alarma de Retroceso', 'Arranque', 'Alternador', 'Rines', 'Tuercas', 
        'Esparragos', 'Freno de Servicio', 'Freno de Seguridad', 'Llanta de Repuesto', 'Llantas', 'Suspensión',
        'Capó', 'Persiana', 'Bumper Delantero', 'Parabrisas', 'Guardafango', 'Stop', 'Bumper Trasero',
        'Vidrio Panorámico Trasero', 'Placa Delantera', 'Placa Trasera', 'Aseo Externo', 'Aseo Interno', 
        'Kit de Carreteras', 'Kit de Herramientas', 'Kit de Botiquín', 'Chaleco Reflectivo', 'Aprobado', 
        'Observaciones'
    ]
    ws.append(headers)
    for preop in preoperacional_diarios:
        ws.append([
            preop.fecha.strftime('%d/%m/%Y'),
            preop.vehiculo.name,
            f"{preop.reporter.first_name} {preop.reporter.last_name}" if preop.reporter else preop.nombre_no_registrado,
            preop.kilometraje,
            preop.get_combustible_level_display(),
            preop.get_aceite_level_display(),
            preop.get_refrigerante_level_display(),
            preop.get_hidraulic_level_display(),
            preop.get_liq_frenos_level_display(),
            preop.get_poleas_display(),
            preop.get_correas_display(),
            preop.get_mangueras_display(),
            preop.get_acoples_display(),
            preop.get_tanques_display(),
            preop.get_radiador_display(),
            preop.get_terminales_display(),
            preop.get_bujes_display(),
            preop.get_rotulas_display(),
            preop.get_ejes_display(),
            preop.get_cruceta_display(),
            preop.get_puertas_display(),
            preop.get_chapas_display(),
            preop.get_manijas_display(),
            preop.get_elevavidrios_display(),
            preop.get_lunas_display(),
            preop.get_espejos_display(),
            preop.get_vidrio_panoramico_display(),
            preop.get_asiento_display(),
            preop.get_apoyacabezas_display(),
            preop.get_cinturon_display(),
            preop.get_aire_display(),
            preop.get_caja_cambios_display(),
            preop.get_direccion_display(),
            preop.get_bateria_display(),
            preop.get_luces_altas_display(),
            preop.get_luces_medias_display(),
            preop.get_luces_direccionales_display(),
            preop.get_cocuyos_display(),
            preop.get_luz_placa_display(),
            preop.get_luz_interna_display(),
            preop.get_pito_display(),
            preop.get_alarma_retroceso_display(),
            preop.get_arranque_display(),
            preop.get_alternador_display(),
            preop.get_rines_display(),
            preop.get_tuercas_display(),
            preop.get_esparragos_display(),
            preop.get_freno_servicio_display(),
            preop.get_freno_seguridad_display(),
            'Sí' if preop.is_llanta_repuesto else 'No',
            preop.get_llantas_display(),
            preop.get_suspencion_display(),
            preop.get_capo_display(),
            preop.get_persiana_display(),
            preop.get_bumper_delantero_display(),
            preop.get_panoramico_display(),
            preop.get_guardafango_display(),
            preop.get_stop_display(),
            preop.get_bumper_trasero_display(),
            preop.get_vidrio_panoramico_trasero_display(),
            preop.get_placa_delantera_display(),
            preop.get_placa_trasera_display(),
            'Sí' if preop.aseo_externo else 'No',
            'Sí' if preop.aseo_interno else 'No',
            'Sí' if preop.kit_carreteras else 'No',
            'Sí' if preop.kit_herramientas else 'No',
            'Sí' if preop.kit_botiquin else 'No',
            'Sí' if preop.chaleco_reflectivo else 'No',
            'Sí' if preop.aprobado else 'No',
            preop.observaciones
        ])

    # Preparar la respuesta HTTP
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename=PreoperacionalDiario_{mes}_{anio}.xlsx'
    wb.save(response)

    return response


class PreoperacionalDiarioUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = PreoperacionalDiario
    form_class = PreoperacionalDiarioForm
    template_name = 'got/preoperacional/preoperacionalform.html'

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
        return reverse('got:preoperacional-detail', kwargs={'pk': self.object.pk})


def gracias_view(request, code):
    equipo = get_object_or_404(Equipo, code=code)
    return render(request, 'got/preoperacional/gracias.html', {'equipo': equipo})


'SOLICITUDES VIEWS'
class SolicitudesListView(LoginRequiredMixin, generic.ListView):
    
    model = Solicitud
    paginate_by = 20
    template_name = 'got/solicitud/solicitud_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['assets'] = Asset.objects.all()

        asset_filter = self.request.GET.get('asset')
        context['asset'] = Asset.objects.filter(abbreviation=asset_filter).first() if asset_filter else None

        context['current_asset'] = self.request.GET.get('asset', '')
        context['current_state'] = self.request.GET.get('state', '')
        context['current_keyword'] = self.request.GET.get('keyword', '')
        return context

    def get_queryset(self):
        queryset = Solicitud.objects.all()
        user = self.request.user
        user_groups = user.groups.values_list('name', flat=True)

        # Aplicar filtros generales de estado, asset y keyword
        state = self.request.GET.get('state')
        asset_filter = self.request.GET.get('asset')
        keyword = self.request.GET.get('keyword')

        if asset_filter:
            queryset = queryset.filter(asset__abbreviation=asset_filter)
        if keyword:
            queryset = queryset.filter(suministros__icontains=keyword)

        # Filtrar según el estado seleccionado
        if state == 'no_aprobada':
            queryset = queryset.filter(approved=False, cancel=False)
        elif state == 'aprobada':
            queryset = queryset.filter(approved=True, sc_change_date__isnull=True, cancel=False)
        elif state == 'tramitado':
            queryset = queryset.filter(approved=True, sc_change_date__isnull=False, cancel=False)
        elif state == 'parcialmente':
            queryset = queryset.filter(satisfaccion=False, recibido_por__isnull=False, cancel=False)
        elif state == 'recibido':
            queryset = queryset.filter(satisfaccion=True, cancel=False)
        elif state == 'cancel':
            queryset = queryset.filter(cancel=True)

        # Aplicar filtros basados en el grupo del usuario
        if 'gerencia' in user_groups:
            # Gerencia puede ver todas las solicitudes
            return queryset
        else:
            # Construir condición de filtrado
            filter_condition = Q()

            if 'operaciones' in user_groups:
                # Usuarios del grupo 'operaciones' pueden ver solicitudes con dpto='o'
                filter_condition |= Q(dpto='o')
            if 'super_members' in user_groups:
                # Usuarios del grupo 'super_members' pueden ver solicitudes con dpto='m'
                filter_condition |= Q(dpto='m')
            if 'maq_members' in user_groups:
                # Usuarios del grupo 'maq_members' pueden ver solicitudes de sus assets supervisados
                supervised_assets = Asset.objects.filter(supervisor=user)
                filter_condition |= Q(asset__in=supervised_assets)
            if 'serport_members' in user_groups:
                # Usuarios del grupo 'serport_members' pueden ver sus propias solicitudes
                filter_condition |= Q(solicitante=user)
            if 'buzos' in user_groups:
                # Usuarios del grupo 'buzos' pueden ver solicitudes de assets de tipo 'buceo'
                buceo_assets = Asset.objects.filter(tipo='buceo')
                filter_condition |= Q(asset__in=buceo_assets)

            # Si no pertenece a ninguno de los grupos anteriores, solo ve sus propias solicitudes
            if not filter_condition:
                filter_condition = Q(solicitante=user)

            # Aplicar el filtro construido al queryset
            queryset = queryset.filter(filter_condition)

        return queryset


def detalle_pdf(request, pk):
    registro = Solicitud.objects.get(pk=pk)
    context = {'rq': registro}
    return render_to_pdf('got/solicitud/solicitud_detail.html', context)


class CreateSolicitudOt(LoginRequiredMixin, View):
    template_name = 'got/solicitud/create-solicitud-ot.html'

    def get(self, request, asset_id, ot_num=None):
        asset = get_object_or_404(Asset, abbreviation=asset_id)
        ot = None if not ot_num else get_object_or_404(Ot, num_ot=ot_num)
        items = Item.objects.all()

        return render(request, self.template_name, {
            'ot': ot,
            'asset': asset,
            'items': items
        })

    def post(self, request, asset_id, ot_num=None):
            asset = get_object_or_404(Asset, abbreviation=asset_id)
            ot = None if not ot_num else get_object_or_404(Ot, num_ot=ot_num)
            items_ids = request.POST.getlist('item_id[]') 
            cantidades = request.POST.getlist('cantidad[]')
            suministros = request.POST.get('suministros', '')
            dpto = request.POST.get('dpto')

            solicitud = Solicitud.objects.create(
                solicitante=request.user,
                requested_by=request.user.get_full_name(),
                ot=ot,
                asset=asset,
                suministros=suministros,
                dpto=dpto,
            )

            for item_id, cantidad in zip(items_ids, cantidades):
                if item_id and cantidad:
                    item = get_object_or_404(Item, id=item_id)
                    Suministro.objects.create(
                        item=item,
                        cantidad=int(cantidad),
                        Solicitud=solicitud
                    )
            return redirect('got:my-tasks')


class EditSolicitudView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        solicitud = get_object_or_404(Solicitud, pk=kwargs['pk'])
        suministros = request.POST.get('suministros')
        if suministros:
            solicitud.suministros = suministros
            solicitud.save()
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    

class ApproveSolicitudView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        solicitud = get_object_or_404(Solicitud, id=kwargs['pk'])
        solicitud.approved = not solicitud.approved
        if solicitud.approved:
            solicitud.approved_by = f"{request.user.first_name} {request.user.last_name}"
            solicitud.approval_date = timezone.now()
        else:
            solicitud.approved_by = ''
            solicitud.approval_date = None
        solicitud.save()
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    

@login_required
def report_received(request, pk):
    if request.method == 'POST':
        solicitud = get_object_or_404(Solicitud, pk=pk)
        satisfaccion = request.POST.get('satisfaccion') == 'True'
        recibido_por = request.POST.get('recibido_por')
        solicitud.satisfaccion = satisfaccion
        solicitud.recibido_por = recibido_por
        solicitud.save()
        return redirect('got:rq-list')
    return redirect('got:rq-list')


@login_required
def update_sc(request, pk):
    if request.method == 'POST':
        solicitud = get_object_or_404(Solicitud, pk=pk)
        num_sc = request.POST.get('num_sc')
        solicitud.num_sc = num_sc
        solicitud.save()

        query_params = {
            'asset': request.POST.get('asset', ''),
            'state': request.POST.get('state', ''),
            'keyword': request.POST.get('keyword', ''),
        }
        
        query_string = '&'.join([f'{key}={value}' for key, value in query_params.items() if value])

        redirect_url = f'{reverse("got:rq-list")}'
        if query_string:
            redirect_url += f'?{query_string}'
        return redirect(redirect_url)
    return redirect('got:rq-list') 


@login_required
def cancel_sc(request, pk):
    if request.method == 'POST':
        solicitud = get_object_or_404(Solicitud, pk=pk)
        reason = request.POST.get('cancel_reason')
        solicitud.cancel_reason = reason
        solicitud.cancel = True
        solicitud.save()
        return redirect('got:rq-list')
    return redirect('got:rq-list')


def download_pdf(request):
    state = request.GET.get('state', '')
    asset_filter = request.GET.get('asset', '')
    keyword = request.GET.get('keyword', '')

    queryset = Solicitud.objects.all()

    if asset_filter:
        queryset = queryset.filter(asset__abbreviation=asset_filter)
    if state:
        if state == 'no_aprobada':
            queryset = queryset.filter(approved=False)
        elif state == 'aprobada':
            queryset = queryset.filter(approved=True, sc_change_date__isnull=True)
        elif state == 'tramitado':
            queryset = queryset.filter(approved=True, sc_change_date__isnull=False)
    if keyword:
        queryset = queryset.filter(suministros__icontains=keyword)

    context = {
        'rqs': queryset,
        'state': state, 
        'asset': Asset.objects.filter(pk=asset_filter).first(),
        'keyword': keyword,
        }
    return render_to_pdf('got/solicitud/rqs_report.html', context)


'SALIDAS VIEW'
class SalListView(LoginRequiredMixin, generic.ListView):

    model = Salida
    paginate_by = 20
    template_name = 'got/salidas/salidas_list.html'


class SalidaCreateView(LoginRequiredMixin, View):
    form_class = SalidaForm
    template_name = 'got/salidas/create-salida.html'

    def get(self, request):
        items = Item.objects.all()
        form = self.form_class()
        image_form = UploadImages(request.POST, request.FILES)

        return render(request, self.template_name, {
            'items': items,
            'form': form,
            'image_form': image_form
        })

    def post(self, request):

            form = self.form_class(request.POST, request.FILES)
            image_form = UploadImages(request.POST, request.FILES)
            items_ids = request.POST.getlist('item_id[]') 
            cantidades = request.POST.getlist('cantidad[]')

            context = {
                'items': Item.objects.all(),
                'form': form,
                'image_form': image_form
            }

            if form.is_valid() and image_form.is_valid():
                solicitud = form.save(commit=False)
                solicitud.responsable = self.request.user.get_full_name()
                solicitud.save()

                for item_id, cantidad in zip(items_ids, cantidades):
                    if item_id and cantidad:
                        item = get_object_or_404(Item, id=item_id)
                        Suministro.objects.create(
                            item=item,
                            cantidad=int(cantidad),
                            salida=solicitud
                        )
                
                for file in request.FILES.getlist('file_field'):
                    Image.objects.create(salida=solicitud, image=file)
                return redirect('got:salida-list')
            return render(request, self.template_name, context)


class NotifySalidaView(LoginRequiredMixin, View):

    def post(self, request, pk):
        salida = get_object_or_404(Salida, pk=pk)
        
        # Obtener y guardar la firma
        signature_data = request.POST.get('signature')
        if signature_data:
            format, imgstr = signature_data.split(';base64,')
            ext = format.split('/')[-1]
            filename = f'signature_{uuid.uuid4()}.{ext}'
            signature_file = ContentFile(base64.b64decode(imgstr), name=filename)
            salida.sign_recibe.save(filename, signature_file, save=True)

        # Enviar el correo electrónico con el PDF adjunto
        pdf_buffer = salida_email_pdf(salida.pk)
        subject = f'Solicitud salida de materiales: {salida}'
        message = f'''
        Cordial saludo,

        Notificación de salida.

        Por favor, revise el archivo adjunto para más detalles.
        '''
        email = EmailMessage(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            ['analistamto@serport.co']  # Puedes añadir más destinatarios aquí
        )
        email.attach(f'Salida_{salida.pk}.pdf', pdf_buffer, 'application/pdf')
        email.send()

        # Redirigir al usuario a la página anterior
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


def salida_pdf(request, pk):
    salida = Salida.objects.get(pk=pk)
    nombre_completo = salida.responsable.split()
    if len(nombre_completo) > 1:
        first_name = nombre_completo[0]
        last_name = nombre_completo[1]
    else:
        first_name = salida.responsable
        last_name = ""

    # Buscar el usuario basado en el nombre y apellido
    try:
        user = User.objects.get(first_name=first_name, last_name=last_name)
        cargo = user.profile.cargo  # Asume que el perfil tiene un campo 'cargo'
    except User.DoesNotExist:
        cargo = 'Cargo no encontrado'
    context = {
        'rq': salida,
        'pro': cargo
        }
    return render_to_pdf('got/salidas/salida_detail.html', context)


def salida_email_pdf(pk):
    salida = Salida.objects.get(pk=pk)
    nombre_completo = salida.responsable.split()
    if len(nombre_completo) > 1:
        first_name = nombre_completo[0]
        last_name = nombre_completo[1]
    else:
        first_name = salida.responsable
        last_name = ""

    # Buscar el usuario basado en el nombre y apellido
    try:
        user = User.objects.get(first_name=first_name, last_name=last_name)
        cargo = user.profile.cargo  # Asume que el perfil tiene un campo 'cargo'
    except User.DoesNotExist:
        cargo = 'Cargo no encontrado'
    context = {
        'rq': salida,
        'pro': cargo
        }
    # pdf_content = render_to_pdf('got/salidas/salida_detail.html', context)

    template = get_template('got/salidas/salida_detail.html')
    html = template.render(context)
    pdf_content = BytesIO()
    pisa.CreatePDF(html, dest=pdf_content)
    return pdf_content.getvalue()

        
class ApproveSalidaView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        solicitud = Salida.objects.get(id=kwargs['pk'])
        solicitud.auth = not solicitud.auth
        solicitud.save()
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    

class SalidaUpdateView(LoginRequiredMixin, View):
    form_class = SalidaForm
    template_name = 'got/salidas/update-salida.html'

    def get(self, request, pk):
        salida = get_object_or_404(Salida, pk=pk)
        form = self.form_class(instance=salida)
        image_form = UploadImages()
        items = Item.objects.all()
        suministros = salida.suministros.all()

        return render(request, self.template_name, {
            'form': form,
            'image_form': image_form,
            'items': items,
            'suministros': suministros,
            'salida': salida,
        })

    def post(self, request, pk):
        salida = get_object_or_404(Salida, pk=pk)
        form = self.form_class(request.POST, request.FILES, instance=salida)
        image_form = UploadImages(request.POST, request.FILES)
        items_ids = request.POST.getlist('item_id[]') 
        cantidades = request.POST.getlist('cantidad[]')

        context = {
            'form': form,
            'image_form': image_form,
            'items': Item.objects.all(),
            'suministros': salida.suministros.all(),
            'salida': salida,
        }

        if form.is_valid() and image_form.is_valid():
            salida = form.save()

            # Manejo de la firma
            signature_data = request.POST.get('signature')
            if signature_data:
                format, imgstr = signature_data.split(';base64,')
                ext = format.split('/')[-1]
                filename = f'signature_{uuid.uuid4()}.{ext}'
                data = ContentFile(base64.b64decode(imgstr), name=filename)
                salida.sign_recibe.save(filename, data, save=True)

            # Actualizar Suministros
            salida.suministros.all().delete()  # Eliminar suministros existentes
            for item_id, cantidad in zip(items_ids, cantidades):
                if item_id and cantidad:
                    item = get_object_or_404(Item, id=item_id)
                    Suministro.objects.create(
                        item=item,
                        cantidad=int(cantidad),
                        salida=salida
                    )

            # Manejo de imágenes
            for file in request.FILES.getlist('file_field'):
                Image.objects.create(salida=salida, image=file)

            # Enviar correo electrónico con el PDF adjunto
            pdf_buffer = salida_email_pdf(salida.pk)
            subject = f'Solicitud salida de materiales: {salida}'
            message = f'''
            Cordial saludo,

            Notificación de salida.

            Por favor, revise el archivo adjunto para más detalles.
            '''
            email = EmailMessage(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                ['seguridad@serport.co']
            )
            email.attach(f'Salida_{salida.pk}.pdf', pdf_buffer, 'application/pdf')
            email.send()


            return redirect('got:salida-list')
        return render(request, self.template_name, context)


'GENERAL VIEWS'
@login_required
def indicadores(request):

    m = 9

    area_filter = request.GET.get('area', None)

    assets = Asset.objects.annotate(num_ots=Count('system__ot'))
    if area_filter:
        assets = assets.filter(area=area_filter)
    top_assets = assets.order_by('-num_ots')[:5]
    ots_per_asset = [a.num_ots for a in top_assets]
    asset_labels = [a.name for a in top_assets]

    labels = ['Preventivo', 'Correctivo', 'Modificativo']

    earliest_start_date = Task.objects.filter(ot=OuterRef('pk')).order_by('start_date').values('start_date')[:1]
    latest_final_date = Task.objects.filter(ot=OuterRef('pk')).annotate(
        final_date=ExpressionWrapper(
            F('start_date') + F('men_time'),
            output_field=DateField()
        )
    ).order_by('-final_date').values('final_date')[:1]

    bar = Ot.objects.annotate(
        start=Subquery(earliest_start_date),
        end=Subquery(latest_final_date)
    ).filter(state='x')

    if area_filter:
        bar = bar.filter(system__asset__area=area_filter)

    barcos = bar.filter(system__asset__area='a')

    if area_filter:
        ots = len(Ot.objects.filter(creation_date__month=m, creation_date__year=2024, system__asset__area=area_filter))

        ot_finish = len(Ot.objects.filter(
            creation_date__month=m,
            creation_date__year=2024, state='f',
            system__asset__area=area_filter))

        preventivo = len(Ot.objects.filter(
            creation_date__month=m,
            creation_date__year=2024,
            tipo_mtto='p',
            system__asset__area=area_filter
            ))
        correctivo = len(Ot.objects.filter(
            creation_date__month=m,
            creation_date__year=2024,
            tipo_mtto='c',
            system__asset__area=area_filter
            ))
        modificativo = len(Ot.objects.filter(
            creation_date__month=m,
            creation_date__year=2024,
            tipo_mtto='m',
            system__asset__area=area_filter
            ))

    else:
        ots = len(Ot.objects.filter(
            creation_date__month=m, creation_date__year=2024))
        ot_finish = len(Ot.objects.filter(
            creation_date__month=m, creation_date__year=2024, state='f'))

        preventivo = len(Ot.objects.filter(
            creation_date__month=m, creation_date__year=2024, tipo_mtto='p'))
        correctivo = len(Ot.objects.filter(
            creation_date__month=m, creation_date__year=2024, tipo_mtto='c'))
        modificativo = len(Ot.objects.filter(
            creation_date__month=m, creation_date__year=2024, tipo_mtto='m'))

    if ots == 0:
        ind_cumplimiento = 0
        data = 0
    else:
        ind_cumplimiento = round((ot_finish/ots)*100, 2)
        data = [
            round((preventivo/ots)*100, 2), round((correctivo/ots)*100, 2),
            round((modificativo/ots)*100, 2)
            ]
        
    assets_a = Asset.objects.filter(area='a')

    # Lista para almacenar los datos de combustible
    combustible_data = []

    # Iterar sobre cada asset y obtener la información de combustible
    for asset in assets_a:
        try:
            # Obtener el suministro de combustible para el asset actual
            suministro = Suministro.objects.get(asset=asset, item_id=132)
            total_quantity = suministro.cantidad

            # Obtener la última transacción de consumo de combustible
            try:
                last_transaction = Transaction.objects.filter(
                    suministro=suministro,
                    tipo='c'  # Asumiendo que 'c' significa 'consumo'
                ).latest('fecha')
                last_report_date = last_transaction.fecha
            except Transaction.DoesNotExist:
                last_report_date = None

                combustible_data.append({
                    'asset_name': asset.name,
                    'last_report_date': last_report_date,
                    'total_quantity': total_quantity,
                })
        except Suministro.DoesNotExist:
            # Si el suministro de combustible no existe para este asset
            combustible_data.append({
                'asset_name': asset.name,
                'last_report_date': None,
                'total_quantity': None,
            })  

    context = {
        'ind_cumplimiento': ind_cumplimiento,
        'data': data,
        'labels': labels,
        'ots': ots,
        'ots_asset': ots_per_asset,
        'asset_labels': asset_labels,
        'ots_finished': ot_finish,
        'barcos': barcos,
        'combustible_data': combustible_data,
    }
    return render(request, 'got/indicadores.html', context)


'EXPERIMENTAL VIEWS'
class ItemManagementView(generic.TemplateView):
    template_name = 'got/item_management.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = Item.objects.all()
        context['form'] = ItemForm()
        return context

    def post(self, request, *args, **kwargs):
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.modified_by = request.user
            form.save()
            return redirect(reverse('got:item_management'))

        context = self.get_context_data(**kwargs)
        context['form'] = form
        return self.render_to_response(context)


def edit_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return redirect(reverse('got:item_management'))
    else:
        form = ItemForm(instance=item)

    return render(request, 'got/edit_item.html', {'form': form, 'item': item})


def export_asset_system_equipo_excel(request):
    # Crear un nuevo libro de trabajo (Excel)
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.title = 'Asset-System-Equipo'

    # Definir los encabezados de la hoja de Excel
    headers = ['Asset', 'System', 'System Code', 'Equipo', 'Equipo Code']
    worksheet.append(headers)

    # Obtener los datos de los Assets, Systems y Equipos
    assets = Asset.objects.prefetch_related('system_set__equipos')

    for asset in assets:
        for system in asset.system_set.all():
            for equipo in system.equipos.all():
                # Agregar una fila para cada Asset, System, Equipo y Equipo Code
                worksheet.append([asset.name, system.name, system.group, equipo.name, equipo.code])

    # Establecer el tipo de contenido de la respuesta HTTP
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=Asset_System_Equipo.xlsx'

    # Guardar el libro de trabajo en la respuesta
    workbook.save(response)

    return response


class DarBajaCreateView(LoginRequiredMixin, CreateView):
    model = DarBaja
    form_class = DarBajaForm
    template_name = 'got/systems/dar_baja_form.html'

    def get_equipo(self):
        equipo_code = self.kwargs.get('equipo_code')
        equipo = get_object_or_404(Equipo, code=equipo_code)
        return equipo

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        equipo = self.get_equipo()
        context['equipo'] = equipo
        return context

    def form_valid(self, form):
        equipo = self.get_equipo()
        user = self.request.user
        # Establecer los campos automáticos
        form.instance.equipo = equipo
        form.instance.reporter = user.get_full_name() if user.get_full_name() else user.username
        form.instance.activo = f"{equipo.system.asset.name} - {equipo.system.name}"

        response = super().form_valid(form)

        # Manejar las firmas
        firma_responsable_data = self.request.POST.get('firma_responsable_data')
        firma_autorizado_data = self.request.POST.get('firma_autorizado_data')

        print('Firma Responsable Data:', self.request.POST.get('firma_responsable_data'))
        print('Firma Autorizado Data:', self.request.POST.get('firma_autorizado_data'))

        if firma_responsable_data:
            format, imgstr = firma_responsable_data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr))
            self.object.firma_responsable.save(f'firma_responsable_{self.object.pk}.{ext}', data, save=True)

        if firma_autorizado_data:
            format, imgstr = firma_autorizado_data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr))
            self.object.firma_autorizado.save(f'firma_autorizado_{self.object.pk}.{ext}', data, save=True)

        # Eliminar rutinas asociadas al equipo
        routines = equipo.equipos.all()
        if routines.exists():
            routines.delete()
            messages.warning(self.request, 'Las rutinas asociadas al equipo han sido eliminadas.')

        # Eliminar registros de horas (HistoryHour)
        history_hours = equipo.hours.all()
        if history_hours.exists():
            history_hours.delete()
            messages.warning(self.request, 'Los registros de horas asociados al equipo han sido eliminados.')

        # Eliminar registros de consumo diario de combustible (DailyFuelConsumption)
        daily_fuel_consumption = equipo.fuel_consumptions.all()
        if daily_fuel_consumption.exists():
            daily_fuel_consumption.delete()
            messages.warning(self.request, 'Los registros de consumo diario de combustible han sido eliminados.')

        # Eliminar registros de Megger
        megger_records = equipo.megger_set.all()
        if megger_records.exists():
            megger_records.delete()
            messages.warning(self.request, 'Los registros de Megger asociados al equipo han sido eliminados.')

        # Eliminar registros preoperacionales
        preoperational_records = equipo.preoperacional_set.all()
        if preoperational_records.exists():
            preoperational_records.delete()
            messages.warning(self.request, 'Los registros preoperacionales asociados al equipo han sido eliminados.')

        # Eliminar suministros (Suministro)
        supplies = equipo.suministros.all()
        if supplies.exists():
            supplies.delete()
            messages.warning(self.request, 'Los suministros asociados al equipo han sido eliminados.')

        # Mover el equipo al sistema con id 445
        new_system = System.objects.get(id=445)
        old_system = equipo.system
        equipo.system = new_system
        equipo.save()
        messages.success(self.request, f'El equipo ha sido trasladado al sistema {new_system.name}.')

        # Redirigir al usuario a la vista del sistema original
        return response
    
    def get_success_url(self):
        old_system = self.get_equipo().system
        return reverse('got:sys-detail', kwargs={'pk': old_system.id})
    



# def is_maq_member(user):
#     return user.groups.filter(name='maq_members').exists()

@login_required
# @user_passes_test(is_maq_member)
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

                # Crear el registro de Overtime
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
                    approved=False  # Por defecto, no aprobado
                )

            return redirect('got:overtime_success')
    else:
        common_form = OvertimeCommonForm()
        person_formset = OvertimePersonFormSet()

    context = {
        'common_form': common_form,
        'person_formset': person_formset,
    }
    return render(request, 'got/overtime_report.html', context)


def overtime_success(request):
    return render(request, 'got/overtime_success.html')


def overtime_list(request):


    person_name = request.GET.get('person_name', '')
    asset_name = request.GET.get('asset', '')
    date_filter = request.GET.get('date', '')


    # Obtener la fecha actual
    today = date.today()

    if today.day < 24:
        # Si estamos antes del día 24, el rango es desde el 24 del mes anterior hasta el 24 del mes actual
        start_date = (today - relativedelta(months=1)).replace(day=24)
        end_date = today.replace(day=24)
    else:
        # Si estamos en o después del día 24, el rango es desde el 24 del mes actual hasta el 24 del siguiente mes
        start_date = today.replace(day=24)
        end_date = (today + relativedelta(months=1)).replace(day=24)

    # Filtrar los registros de Overtime en el rango de fechas
    overtime_entries = Overtime.objects.filter(fecha__gte=start_date, fecha__lt=end_date)


    if person_name:
        overtime_entries = overtime_entries.filter(nombre_completo__icontains=person_name)

    if asset_name:
        overtime_entries = overtime_entries.filter(asset__name__icontains=asset_name)

    if date_filter:
        overtime_entries = overtime_entries.filter(fecha=date_filter)

    overtime_entries = overtime_entries.order_by('fecha', 'asset', 'justificacion')

    paginator = Paginator(overtime_entries, 25)  # Mostrar 25 registros por página

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Agrupar los registros por fecha y activo
    date_asset_justification_groups = []

    for fecha, fecha_entries in groupby(page_obj.object_list, key=attrgetter('fecha')):
        asset_groups = []
        fecha_entries = list(fecha_entries)
        # Agrupar por activo dentro de cada fecha
        for asset, asset_entries in groupby(fecha_entries, key=attrgetter('asset')):
            asset_entries = list(asset_entries)
            # Agrupar por justificación dentro de cada activo
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

    context = {
        'date_asset_groups': date_asset_justification_groups,
        'page_obj': page_obj,
    }

    return render(request, 'got/overtime_list.html', context)


@login_required
@permission_required('got.can_approve_overtime', raise_exception=True)
def approve_overtime(request, pk):
    if request.method == 'POST':
        overtime_entry = get_object_or_404(Overtime, pk=pk)
        # Cambiar el estado de aprobación
        overtime_entry.approved = not overtime_entry.approved
        overtime_entry.save()
    return redirect('got:overtime_list')

 
@login_required
def edit_overtime(request, pk):
    overtime_entry = get_object_or_404(Overtime, pk=pk)
    if request.method == 'POST':
        form = OvertimeEditForm(request.POST, instance=overtime_entry)
        if form.is_valid():
            form.save()
            return redirect('got:overtime_list')
    return redirect('got:overtime_list')

@login_required
def delete_overtime(request, pk):
    overtime_entry = get_object_or_404(Overtime, pk=pk)
    if request.method == 'POST':
        overtime_entry.delete()
        return redirect('got:overtime_list')
    return redirect('got:overtime_list')




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

    # Aplicar los mismos filtros que en la vista de lista
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

    # Crear el libro de Excel
    wb = openpyxl.Workbook()
    ws = wb.active

    # Crear el encabezado personalizado
    last_month = today - relativedelta(months=1)
    report_title = f"REPORTE 24 {last_month.strftime('%B')} hasta 24 {today.strftime('%B')} {today.year}"
    ws.append([report_title])
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=8)
    ws.cell(row=1, column=1).font = openpyxl.styles.Font(size=14, bold=True)

    # Añadir los encabezados de columna
    headers = ['Nombre completo', 'Cédula', 'Fecha', 'Justificación', 'Hora inicio', 'Hora fin', 'Aprueba', 'Transporte']
    ws.append(headers)

    # Establecer estilos para los encabezados
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



from django.contrib.auth.views import PasswordResetView


class CustomPasswordResetView(PasswordResetView):
    email_template_name = 'registration/password_reset_email.txt'  # Plantilla de texto plano
    html_email_template_name = 'registration/password_reset_email.html'  # Plantilla HTML
    subject_template_name = 'registration/password_reset_subject.txt'  # Plantilla para el asunto
    domain_override = settings.MY_SITE_DOMAIN  # Establece el dominio

    def get_extra_email_context(self):
        # Determinar el protocolo
        protocol = 'https' if self.request.is_secure() else 'http'

        # Obtener el nombre del sitio
        site_name = settings.MY_SITE_NAME  # Define esto en settings.py

        return {
            'protocol': protocol,
            'domain': self.domain_override,
            'site_name': site_name,
        }
    