from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import permission_required, login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group, User
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage, send_mail
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Count, Q, Min, OuterRef, Subquery, F, ExpressionWrapper, DateField, Prefetch, Sum, Max
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import get_template, render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.timezone import localdate
from django.views import generic, View
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from .models import *
from .forms import *

from datetime import timedelta, date, datetime
from xhtml2pdf import pisa
from io import BytesIO
import itertools
import PyPDF2
import logging
import base64
import uuid
import pandas as pd
import calendar

from .functions import *


logger = logging.getLogger(__name__)


'HOME PAGE'
class AssignedTaskByUserListView(LoginRequiredMixin, generic.ListView):

    model = Task
    template_name = 'got/task/assignedtasks_list_pendient.html'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        current_user = request.user
        if current_user.groups.filter(name='gerencia').exists():
            return redirect('got:asset-list')
        elif request.user.username == 'elkin':
            return redirect('got:asset-detail', pk='VEH')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_user = self.request.user
        all_users = User.objects.none()

        asset_id = self.request.GET.get('asset_id')
        if asset_id:
            context['selected_asset_name'] = Asset.objects.get(abbreviation=asset_id)
            context['asset_id'] = asset_id

        worker_id = self.request.GET.get('worker')
        if worker_id: 
            worker = User.objects.get(id=worker_id)
            context['worker'] = f'{worker.first_name} {worker.last_name}'
            context['worker_id'] = worker_id

        if current_user.groups.filter(name__in=['maq_members', 'buzos_members']).exists():
            talleres = Group.objects.get(name='serport_members')
            taller_list = list(talleres.user_set.all())
            taller_list.append(current_user)
            all_users = User.objects.filter(id__in=[user.id for user in taller_list])
        elif current_user.groups.filter(name='super_members').exists():
            all_users = User.objects.all()

        context['assets'] = Asset.objects.all()
        context['serport_members'] = all_users

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

        if current_user.groups.filter(name='super_members').exists():
            return queryset


        if current_user.groups.filter(name='maq_members').exists():
            return queryset.filter(ot__system__asset__supervisor=current_user)

        if current_user.groups.filter(name='buzos_members').exists():
            locations = buzos_station_filter(self.request.user)
            if locations:
                return queryset.filter(ot__system__asset__area='b', ot__system__location__in=locations)
            return queryset.filter(ot__system__asset__area='b')

        return queryset.none() 
    
 
'ASSETS VIEWS'
class AssetsListView(LoginRequiredMixin, generic.ListView):

    model = Asset
    paginate_by = 20

    def get_queryset(self):
        queryset = Asset.objects.all()
        area = self.request.GET.get('area')
        user_groups = self.request.user.groups.values_list('name', flat=True)
        if 'buzos_members' in user_groups:
            queryset = queryset.filter(area='b')
        if area:
            queryset = queryset.filter(area=area)

        return queryset


class AssetDetailView(LoginRequiredMixin, generic.DetailView):

    model = Asset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset = self.get_object()
        systems = asset.system_set.all()

        other_asset_systems = System.objects.filter(location=asset.name).exclude(asset=asset)
        combined_systems = (systems.union(other_asset_systems)).order_by('group')
        paginator = Paginator(combined_systems, 10)

        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # if self.request.user.groups.filter(name='buzos_members').exists():
        #     locations = buzos_station_filter(self.request.user)
        #     if locations:
        #         return asset.system_set.filter(location__in=locations)
        #     return asset.system_set.all()

        current_month_name_en = datetime.now().strftime('%B')
        current_month_name_es = traductor(current_month_name_en)

        form = RutinaFilterForm(self.request.GET or None, asset=asset)

        if form.is_valid():
            current_month_name_en = form.cleaned_data.get('month')
            current_month_name_es = traductor(calendar.month_name[int(current_month_name_en)])
            month = int(form.cleaned_data['month'])
            year = int(form.cleaned_data['year'])
            show_execute = form.cleaned_data.get('execute', False)
            selected_locations = form.cleaned_data.get('locations')

            filtered_rutas = Ruta.objects.filter(system__in=systems, system__location__in=selected_locations).exclude(system__state__in=['x', 's']).order_by('-nivel', 'frecuency')
            if show_execute == 'on':
                filtered_rutas = [
                    ruta for ruta in filtered_rutas if (ruta.next_date and ruta.next_date.month <= month and ruta.next_date.year == year) or (ruta.ot and ruta.ot.state == 'x') or (ruta.percentage_remaining < 15)
                    ]
            else:
                filtered_rutas = [
                    ruta for ruta in filtered_rutas if (ruta.next_date and ruta.next_date.month <= month and ruta.next_date.year == year) or (ruta.percentage_remaining < 15)
                    ]

        else:
            filtered_rutas = Ruta.objects.filter(system__in=systems).exclude(system__state__in=['x', 's']).order_by('-nivel', 'frecuency')
            filtered_rutas = [ruta for ruta in filtered_rutas if (ruta.percentage_remaining < 15)]

        if asset.area == 'b':
            context['locations'] = System.objects.filter(asset=asset).values_list('location', flat=True).distinct()

        context['sys_form'] = SysForm()
        context['page_obj'] = page_obj
        context['page_obj_rutas'] = filtered_rutas
        context['mes'] = current_month_name_es

        rotativos = Equipo.objects.filter(system__asset=asset, tipo='r').exists()
        context['rotativos'] = rotativos
        context['other_asset_systems'] = other_asset_systems
        context['add_sys'] = combined_systems

        context['items_by_subsystem'] = consumibles_summary(asset)
        context['rutinas_filter_form'] = form

        return context
                
    def export_rutinas_to_excel(self):
        asset = self.get_object()
        systems = asset.system_set.all()

        # Obtén las rutas filtradas de acuerdo a los criterios que se aplican en la vista
        filtered_rutas, _ = self.get_filtered_rutas(asset, systems)
        data = []

        for ruta in filtered_rutas:
            # Información de la rutina
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
                'activity': '---',  # Placeholder para la fila de la rutina en la columna de actividades
                'responsable': ''  # Columna vacía para la fila de la rutina
            })

            # Actividades relacionadas con esta rutina
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
                    'activity': f'- {task.description}',  # Descripción de la tarea con un guion para indentación
                    'responsable': responsable_name
                })

        # Convertimos la lista de diccionarios en un DataFrame
        df = pd.DataFrame(data)
        df.columns = ['Equipo', 'Ubicación', 'Código', 'Frecuencia', 'Control', 'Tiempo Restante', 'Última Intervención', 'Próxima Intervención', 'Orden de Trabajo', 'Actividad', 'Responsable']

        # Generamos la respuesta HTTP con el archivo Excel
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="rutinas.xlsx"'
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)

        return response


    def get_filtered_rutas(self, asset, systems):
        form = RutinaFilterForm(self.request.GET or None, asset=asset)
        current_month_name_en = datetime.now().strftime('%B')
        current_month_name_es = traductor(current_month_name_en)

        if form.is_valid():
            current_month_name_en = form.cleaned_data.get('month')
            current_month_name_es = traductor(calendar.month_name[int(current_month_name_en)])
            month = int(form.cleaned_data['month'])
            year = int(form.cleaned_data['year'])
            show_execute = form.cleaned_data.get('execute', False)
            selected_locations = form.cleaned_data.get('locations')

            filtered_rutas = Ruta.objects.filter(system__in=systems, system__location__in=selected_locations).exclude(system__state__in=['x', 's']).order_by('-nivel', 'frecuency')
            if show_execute == 'on':
                filtered_rutas = [
                    ruta for ruta in filtered_rutas if (ruta.next_date and ruta.next_date.month <= month and ruta.next_date.year == year) or (ruta.ot and ruta.ot.state == 'x')
                ]
            else:
                filtered_rutas = [
                    ruta for ruta in filtered_rutas if (ruta.next_date and ruta.next_date.month <= month and ruta.next_date.year == year)
                ]
        else:
            filtered_rutas = Ruta.objects.filter(system__in=systems).exclude(system__state__in=['x', 's']).order_by('-nivel', 'frecuency')
            filtered_rutas = [ruta for ruta in filtered_rutas if (ruta.percentage_remaining < 10)]

        return filtered_rutas, current_month_name_es

    def post(self, request, *args, **kwargs):
        asset = self.get_object()
        sys_form = SysForm(request.POST)

        if 'download_excel' in request.POST:
            return self.export_rutinas_to_excel()
        
        if sys_form.is_valid():
            sys = sys_form.save(commit=False)
            sys.asset = asset
            sys.save()
            return redirect(request.path)
        else:
            context = {'asset': asset, 'sys_form': sys_form}
            return render(request, self.template_name, context)


def preventivo_pdf(request, pk):
    asset = get_object_or_404(Asset, pk=pk)
    
    # Obtener los sistemas asociados al Asset
    systems = asset.system_set.all()
    
    # Reutilizar la lógica de filtrado de rutas
    asset_detail_view = AssetDetailView()
    asset_detail_view.request = request  # Asignamos el request actual a la vista para utilizar su lógica
    filtered_rutas, current_month_name_es = asset_detail_view.get_filtered_rutas(asset, systems)
    
    # Pasar los datos filtrados al contexto
    context = {
        'rq': asset,
        'filtered_rutas': filtered_rutas,
        'mes': current_month_name_es,
    }
    return render_to_pdf('got/assets/asset-routine.html', context)


class AssetDocCreateView(generic.View):
    form_class = DocumentForm
    template_name = 'got/add-document.html'

    def get(self, request, asset_id):
        asset = get_object_or_404(Asset, pk=asset_id)
        form = self.form_class()
        return render(request, self.template_name, {'form': form, 'asset': asset})

    def post(self, request, asset_id):
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.asset = get_object_or_404(Asset, pk=asset_id)
            document.save()
            return redirect('got:asset-detail', pk=asset_id)
        return render(request, self.template_name, {'form': form})


def asset_suministros_report(request, abbreviation):
    asset = get_object_or_404(Asset, abbreviation=abbreviation)
    suministros = Suministro.objects.filter(asset=asset)

    ultima_fecha_transaccion = TransaccionSuministro.objects.filter(
        suministro__asset=asset
    ).aggregate(Max('fecha'))['fecha__max'] or "---"

    if request.method == 'POST':
        for suministro in suministros:
            cantidad_consumida = int(request.POST.get(f'consumido_{suministro.id}', 0))
            cantidad_ingresada = int(request.POST.get(f'ingresado_{suministro.id}', 0))
            
            suministro.cantidad -= cantidad_consumida
            suministro.cantidad += cantidad_ingresada
            suministro.save()
            TransaccionSuministro.objects.create(
                suministro=suministro,
                cantidad_ingresada=cantidad_ingresada,
                cantidad_consumida=cantidad_consumida,
                usuario=request.user
            )
        return redirect(reverse('got:asset-detail', kwargs={'pk': asset.abbreviation}))

    return render(request, 'got/asset_suministros_report.html', {'asset': asset, 'suministros': suministros, 'ultima_fecha_transaccion': ultima_fecha_transaccion})


@login_required
def schedule(request, pk):

    tasks = Task.objects.filter(ot__system__asset=pk, ot__isnull=False, start_date__isnull=False, ot__state='x')
    ots = Ot.objects.filter(system__asset=pk, state='x')
    asset = get_object_or_404(Asset, pk=pk)
    systems = System.objects.filter(asset=asset)
    min_date = tasks.aggregate(Min('start_date'))['start_date__min']

    color_palette = itertools.cycle([
        'rgba(255, 99, 132, 0.2)',   # rojo
        'rgba(54, 162, 235, 0.2)',   # azul
        'rgba(255, 206, 86, 0.2)',   # amarillo
        'rgba(75, 192, 192, 0.2)',   # verde agua
        'rgba(153, 102, 255, 0.2)',  # púrpura
        'rgba(255, 159, 64, 0.2)',   # naranja
    ])

    n = 0
    responsibles = set(task.responsible.username for task in tasks if task.responsible)
    responsible_colors = {res: next(color_palette) for res in responsibles}

    chart_data = []
    n = 0
    for task in tasks:
        if task.finished:
            color = "rgba(192, 192, 192, 0.5)"
            border_color = "rgba(192, 192, 192, 1)"
        else:
            color = responsible_colors.get(task.responsible.username, "rgba(54, 162, 235, 0.2)")
            border_color = color.replace('0.2', '1') 
        
        chart_data.append({
            'start_date': task.start_date,
            'final_date': task.final_date,
            'description': truncate_text(task.ot.description),
            'name': f"{task.responsible.first_name} {task.responsible.last_name}",
            'activity_description': task.description,
            'background_color': color,
            'border_color': border_color,
        })
        n += 1

    context = {
        'tasks': chart_data,
        'asset': asset,
        'min_date': min_date,
        'responsibles': responsible_colors,
    }
    return render(request, 'got/schedule.html', context)


def generate_asset_pdf(request, asset_id):
    asset = get_object_or_404(Asset, pk=asset_id)
    systems = asset.system_set.all()

    systems_with_rutas = []
    for system in systems:
        rutas_data = []
        rutas = Ruta.objects.filter(system=system).prefetch_related('task_set')
        for ruta in rutas:
            # Recoger las tareas para cada ruta
            tasks = ruta.task_set.all()
            rutas_data.append({
                'ruta': ruta,
                'tasks': tasks,
                'ot_num': ruta.ot.num_ot if ruta.ot else 'N/A'  # Asegúrate que ruta.ot es accesible y no nulo
            })
        systems_with_rutas.append({
            'system': system,
            'rutas_data': rutas_data
        })

    context = {
        'asset': asset,
        'systems_with_rutas': systems_with_rutas
    }

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Asset_{}.pdf"'.format(asset.pk)
    template = get_template('got/asset_pdf_template.html')
    html = template.render(context)
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response


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


class SysDelete(DeleteView):

    model = System

    def get_success_url(self):
        asset_code = self.object.asset.id
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

    return render_to_pdf('got//systems/system_pdf_template.html', context)


'EQUIPMENTS VIEW'
class EquipoCreateView(CreateView):

    model = Equipo
    form_class = EquipoForm
    template_name = 'got/equipo_form.html'

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

        return super().form_valid(form)

    def get_success_url(self):
        return reverse('got:sys-detail', kwargs={'pk': self.object.system.pk})
    

class EquipoUpdate(UpdateView):

    model = Equipo
    form_class = EquipoFormUpdate
    template_name = 'got/equipo_form.html'
    http_method_names = ['get', 'post']


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


'HOURS VIEW'
@login_required
def reporthours(request, component):

    hours = HistoryHour.objects.filter(component=component)[:30]
    equipo = get_object_or_404(Equipo, pk=component)

    if request.method == 'POST':
        # Si se envió el formulario, procesarlo
        form = ReportHours(request.POST)
        if form.is_valid():
            # Guardar el formulario si es válido
            instance = form.save(commit=False)
            instance.component = equipo
            instance.reporter = request.user
            instance.save()
            return redirect(request.path)
    else:
        form = ReportHours()

    context = {
        'form': form,
        'horas': hours,
        'component': equipo
    }

    return render(request, 'got/hours.html', context)


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['assets'] = Asset.objects.filter(area='a')
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        asset_id = self.request.GET.get('asset_id')

        if asset_id:
            queryset = queryset.filter(equipo__system__asset_id=asset_id)

        if self.request.user.groups.filter(name='maq_members').exists():
            supervised_assets = Asset.objects.filter(
                supervisor=self.request.user)

            queryset = queryset.filter(
                equipo__system__asset__in=supervised_assets)
        elif self.request.user.groups.filter(name='buzos_members').exists():
            supervised_assets = Asset.objects.filter(area='b')

            queryset = queryset.filter(equipo__system__asset__in=supervised_assets)

        return queryset
    

class FailureDetailView(LoginRequiredMixin, generic.DetailView):

    model = FailureReport


class FailureReportForm(LoginRequiredMixin, CreateView):
    model = FailureReport
    form_class = failureForm
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
            'reporter': self.object.reporter,
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
            form.instance.reporter = request.user
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
    http_method_names = ['get', 'post']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset = self.get_object().equipo.system.asset
        context['asset_main'] = asset
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        asset = self.get_object().equipo.system.asset
        form.fields['equipo'].queryset = Equipo.objects.filter(
            system__asset=asset)
        return form

    def form_valid(self, form):
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
    )
    nueva_ot.save()

    fail.related_ot = nueva_ot
    fail.save()

    return redirect('got:ot-detail', pk=nueva_ot.pk)


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
        else:
            context['task_form'] = ActFormNoSup()

        context['all_tasks_finished'] = not self.get_object().task_set.filter(finished=False).exists()
        context['has_activities'] = self.get_object().task_set.exists()

        failure_report = FailureReport.objects.filter(related_ot=self.get_object())
        context['failure_report'] = failure_report
        context['failure'] = failure_report.exists()

        rutas = self.get_object().ruta_set.all()
        context['rutas'] = rutas
        context['equipos'] = set([ruta.equipo for ruta in rutas])

        system = self.get_object().system
        context['electric_motors'] = system.equipos.filter(tipo='e')
        context['has_electric_motors'] = system.equipos.filter(tipo='e').exists()
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
            task.delete()
            return redirect(ot.get_absolute_url()) 
    
        task_form_class = ActForm if request.user.groups.filter(name='super_members').exists() else ActFormNoSup
        task_form = task_form_class(request.POST, request.FILES)
        image_form = UploadImages(request.POST, request.FILES)

        if task_form.is_valid() and image_form.is_valid():
            task = task_form.save(commit=False)
            task.ot = ot
            task.save()

            for file in request.FILES.getlist('file_field'):
                Image.objects.create(task=task, image=file)

        state_form = FinishOtForm(request.POST)

        if 'finish_ot' in request.POST and state_form.is_valid():
            self.object.state = 'f'
            signature_data = request.POST.get('sign_supervisor')

            rutas_relacionadas = Ruta.objects.filter(ot=ot)
            for ruta in rutas_relacionadas:
                actualizar_rutas_dependientes(ruta)

            fallas_relacionadas = FailureReport.objects.filter(related_ot=ot)
            for fail in fallas_relacionadas:
                fail.closed = True
                fail.save()

            # supervisor = ot.system.asset.supervisor
            # if supervisor and supervisor.email:
            #     supervisor_email = supervisor.email

            if signature_data:
                format, imgstr = signature_data.split(';base64,')
                ext = format.split('/')[-1]
                filename = f'supervisor_signature_{uuid.uuid4()}.{ext}'
                data = ContentFile(base64.b64decode(imgstr), name=filename)
                self.object.sign_supervision.save(filename, data, save=True)
                self.object.save()

                # Enviar correo electrónico al finalizar la OT
                # subject = f'Orden de Trabajo {ot.num_ot} Finalizada'
                # message = render_to_string('got/ot_finished_email.txt', {'ot': ot})
                # from_email = settings.EMAIL_HOST_USER
                # to_email = supervisor_email

                # email = EmailMessage(
                #     subject, message, from_email, [to_email]
                #     )

                # # Adjuntar el PDF al correo
                # pdf_content_dynamic = generate_pdf_content(ot)
                # pdf_filename_dynamic = f'OT_{ot.num_ot}_Detalle.pdf'
                # email.attach(
                #     pdf_filename_dynamic,
                #     pdf_content_dynamic,
                #     'application/pdf'
                #     )

                # Adjuntar el PDF almacenado en el campo info_contratista_pdf
                # if ot.info_contratista_pdf:
                #     pdf_filename_stored = f'OT_{ot.num_ot}_Contratista.pdf'
                #     email.attach(
                #         pdf_filename_stored,
                #         ot.info_contratista_pdf.read(),
                #         'application/pdf'
                #         )

                # try:
                #     # Preparar y enviar el correo electrónico
                #     email.send()
                # except smtplib.SMTPSenderRefused as e:
                #     # Manejar adecuadamente el error
                #     logger.error(f"Error al enviar correo: {str(e)}")
                #     messages.error(request, "No se pudo enviar el correo. El tamaño del mensaje excede el límite permitido.")
                #     return redirect(ot.get_absolute_url())

            return redirect(ot.get_absolute_url())

        elif 'submit_task' in request.POST and task_form.is_valid():
            act = task_form.save(commit=False)
            act.ot = ot
            if isinstance(task_form, ActFormNoSup):
                act.responsible = request.user
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
    nueva_ot = Ot(
        description=f"Rutina de mantenimiento con código {ruta.name}",
        state='x',
        supervisor=f"{request.user.first_name} {request.user.last_name}",
        tipo_mtto='p',
        system=ruta.system,
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
            )

        ruta.ot = ot
        ruta.save()

        if ruta.dependencia:
            copiar_tasks_y_actualizar_ot(ruta.dependencia, ot)

    copiar_tasks_y_actualizar_ot(ruta, nueva_ot)
    return redirect('got:ot-detail', pk=nueva_ot.pk)




def rutina_form_view(request, ruta_id):
    ruta = get_object_or_404(Ruta, code=ruta_id)
    tasks = Task.objects.filter(ruta=ruta)
    fecha_actual = timezone.now().date()
    fecha_seleccionada = request.POST.get('fecha', fecha_actual)
    ot_state = 'f' 

    if request.method == 'POST':
        formset_data = []
        for task in tasks:
            realizado = request.POST.get(f'realizado_{task.id}') == 'on'
            observaciones = request.POST.get(f'observaciones_{task.id}')
            evidencias = request.FILES.getlist(f'evidencias_{task.id}')
            
            if not realizado:
                ot_state = 'x'
            
            formset_data.append({
                'task': task,
                'realizado': realizado,
                'observaciones': observaciones,
                'evidencias': evidencias
            })

        signature_data = request.POST.get('signature')
        signature_file = None
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
            sign_supervision=signature_file
        )
            
        for form_data in formset_data:
            new_task = Task.objects.create(
                ot=new_ot,
                description=form_data['task'].description,
                responsible=request.user,
                news=form_data['observaciones'],
                finished=form_data['realizado'],
                start_date=fecha_seleccionada
            )
            # Guardar evidencias si las hay
            for evidencia in form_data['evidencias']:
                Image.objects.create(task=new_task, image=evidencia)
        ruta.intervention_date = fecha_seleccionada
        ruta.ot = new_ot
        ruta.save()
        print("Nueva OT creada con éxito:", new_ot)
        return redirect(ruta.system.get_absolute_url)

    else:
        formset_data = [{'task': task, 'form': ActivityForm(), 'upload_form': UploadImages()} for task in tasks]

    return render(request, 'got/ruta_ot_form.html', 
                  {'formset_data': formset_data, 'ruta': ruta, 'fecha_seleccionada': fecha_seleccionada,}
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
def OperationListView(request):

    assets = Asset.objects.filter(area='a')
    operations = Operation.objects.order_by('start')

    operations_data = []
    for asset in assets:
        asset_operations = asset.operation_set.all().values(
            'start', 'end', 'proyecto', 'requirements'
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

    context= {
        'operations_data': operations_data,
        'operation_form': form,
        'modal_open': modal_open,
        'operaciones': operations,
        }

    return render(request, 'got/operation_list.html', context)


class OperationUpdate(UpdateView):

    model = Operation
    form_class = OperationForm

    def get_success_url(self):

        return reverse('operation-list')


class OperationDelete(DeleteView):

    model = Operation
    success_url = reverse_lazy('got:operation-list')


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


class SalidaDetailView(LoginRequiredMixin, generic.DetailView):

    model = Preoperacional
    template_name = 'got/preoperacional/salida_detail.html'


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


class PreoperacionalDetailView(LoginRequiredMixin, generic.DetailView):

    model = PreoperacionalDiario
    template_name = 'got/preoperacional/preoperacional_detail.html'


def preoperacional_diario_view(request, code):
    
    equipo = get_object_or_404(Equipo, code=code)
    rutas_vencidas = [ruta for ruta in equipo.equipos.all() if ruta.next_date < date.today()]

    existente = PreoperacionalDiario.objects.filter(vehiculo=equipo, fecha=localdate()).first()

    if existente:
        mensaje = f"El preoperacional del vehículo {equipo} de la fecha actual ya fue diligenciado y exitosamente enviado. El resultado fue: {'Aprobado' if existente.aprobado else 'No aprobado'}."
        # Mostrar un modal o mensaje con Django messages framework
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
        state = self.request.GET.get('state')
        asset_filter = self.request.GET.get('asset')

        if asset_filter:
            queryset = queryset.filter(asset__abbreviation=asset_filter)

        if self.request.user.groups.filter(name='maq_members').exists():
            supervised_assets = Asset.objects.filter(
                supervisor=self.request.user)
            queryset = queryset.filter(asset__in=supervised_assets)

        keyword = self.request.GET.get('keyword')
        if keyword:
            queryset = queryset.filter(suministros__icontains=keyword)

        if state == 'no_aprobada':
            queryset = queryset.filter(approved=False, cancel=False)
        elif state == 'aprobada':
            queryset = queryset.filter(approved=True, sc_change_date__isnull=True, cancel=False)
        elif state == 'tramitado':
            queryset = queryset.filter(approved=True, sc_change_date__isnull=False, cancel=False)
        elif state == 'cancel':
            queryset = queryset.filter(cancel=True)

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

            solicitud = Solicitud.objects.create(
                solicitante=request.user,
                ot=ot,
                asset=asset,
                suministros=suministros
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
    def get(self, request, *args, **kwargs):
        solicitud = Solicitud.objects.get(id=kwargs['pk'])
        solicitud.approved = not solicitud.approved
        solicitud.save()
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


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

                signature_data = request.POST.get('signature')
                if signature_data:
                    format, imgstr = signature_data.split(';base64,') 
                    ext = format.split('/')[-1]
                    filename = f'signature_{uuid.uuid4()}.{ext}'
                    data = ContentFile(base64.b64decode(imgstr), name=filename)
                    solicitud.sign_recibe.save(filename, data, save=True)
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
                
                # pdf_buffer = salida_email_pdf(solicitud.pk)
                # subject = f'Solicitud salida de materiales: {solicitud}'
                # message = f'''
                # Cordial saludo,
                
                # Notificación de salida.
                
                # Por favor, revise el archivo adjunto para más detalles.
                # '''
                # email = EmailMessage(
                #     subject,
                #     message,
                #     settings.EMAIL_HOST_USER,
                #     ['analistamto@serport.co']#, 'seguridad@serport.co']
                # )
                # email.attach(f'Salida_{solicitud.pk}.pdf', pdf_buffer, 'application/pdf')
                # email.send()
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
    

'GENERAL VIEWS'
@login_required
def indicadores(request):

    m = 8

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

    context = {
        'ind_cumplimiento': ind_cumplimiento,
        'data': data,
        'labels': labels,
        'ots': ots,
        'ots_asset': ots_per_asset,
        'asset_labels': asset_labels,
        'ots_finished': ot_finish,
        'barcos': barcos
    }
    return render(request, 'got/indicadores.html', context)


'EXPERIMENTAL VIEWS'
def add_location(request):
    if request.method == 'POST':
        form = LocationForm(request.POST)
        if form.is_valid():
            location = form.save()
            return redirect('view-location', pk=location.pk)
    else:
        form = LocationForm()
    return render(request, 'got/add_location.html', {'form': form})

def view_location(request, pk):
    location = get_object_or_404(Location, pk=pk)
    return render(request, 'got/view_location.html', {'location': location})


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


