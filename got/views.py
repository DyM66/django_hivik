import base64
import logging
import uuid
import json
from datetime import timedelta, date, datetime
from decimal import Decimal
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import permission_required, login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.auth.views import PasswordResetView
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Count, Q, OuterRef, Subquery, F, ExpressionWrapper, DateField, Prefetch, Sum, Max, Case, When, IntegerField, BooleanField, Value
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.timezone import localdate
from django.utils.translation import gettext as _
from django.views import generic, View
from django.views.decorators.cache import never_cache, cache_control
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from megger_app.models import Megger
from taggit.models import Tag 
from .utils import *
from .models import *
from .forms import *
from django.db import transaction, IntegrityError

logger = logging.getLogger(__name__)


'ASSETS VIEWS'
class AssetsListView(LoginRequiredMixin, TemplateView):
    template_name = 'got/assets/asset_list.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Redirige a:
          - El primer asset supervisado (maq_members).
          - Las tareas si es serport_members.
          - Caso contrario => mostrar la lista normal.
        """
        user = request.user
        if user.groups.filter(name__in=['maq_members', 'buzos_members']).exists():
            asset = Asset.objects.filter(models.Q(supervisor=request.user) | models.Q(capitan=request.user)).first()

            if asset:
                return redirect('got:asset-detail', pk=asset.abbreviation)
        elif user.groups.filter(name='serport_members').exists():
            return redirect('got:my-tasks')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        asset_pk = request.POST.get('asset_pk')
        if not asset_pk:
            messages.error(request, "No se ha especificado el asset a actualizar.")
            return redirect('got:asset-list')

        asset = get_object_or_404(Asset, pk=asset_pk)
        action = request.POST.get('action')

        if action == 'update_place':
            place_id = request.POST.get('selected_place')
            if place_id:
                place = get_object_or_404(Place, pk=place_id)
                asset.place = place
                asset.save()
                messages.success(request, "La ubicación del asset se ha actualizado correctamente.")
            else:
                messages.error(request, "No se seleccionó ninguna ubicación.")

        elif action == 'update_supervisor':
            supervisor = asset.supervisor
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            if not first_name or not last_name:
                messages.error(request, "El nombre y el apellido del supervisor son requeridos.")
                return redirect('got:asset-list')
            supervisor.first_name = first_name
            supervisor.last_name = last_name
            supervisor.save()
            messages.success(request, "Supervisor actualizado correctamente.")

        elif action == 'update_capitan':
            capitan = asset.capitan
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            if not first_name or not last_name:
                messages.error(request, "El nombre y el apellido del capitán son requeridos.")
                return redirect('got:asset-list')
            capitan.first_name = first_name
            capitan.last_name = last_name
            capitan.save()
            messages.success(request, "Capitán actualizado correctamente.")

        else:
            messages.error(request, "Acción no reconocida.")
        return redirect('got:asset-list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        areas = {
            'a': 'Motonave',
            'c': 'Barcazas',
            'o': 'Oceanografía',
            'l': 'Locativo',
            'v': 'Vehiculos',
            'x': 'Apoyo'
        }
        assets = Asset.objects.filter(show=True)
        context['all_assets'] = Asset.objects.filter(show=True).order_by('name')
        context['assets_by_area'] = {area_name: [asset for asset in assets if asset.area == area_code] for area_code, area_name in areas.items()}

        context['area_icons'] = {
            'a': 'fa-ship',            # Motonave
            'c': 'fa-solid fa-ferry',
            'o': 'fa-water',           # Oceanografía
            'l': 'fa-building',        # Locativo
            'v': 'fa-car',             # Vehículos
            'x': 'fa-cogs',            # Apoyo
        }

        context['places'] = Place.objects.all()
        context['supervisors'] = User.objects.filter(groups__name__in=['maq_members', 'super_members'])
        context['capitanes'] = User.objects.filter(groups__name='maq_members')

        open_failures_dict = {}
        for asset in assets:
            # Filtramos las fallas abiertas de este asset
            fr_qs = FailureReport.objects.filter(closed=False, equipo__system__asset=asset)
            crit_qs = fr_qs.filter(critico=True)
            no_crit_qs = fr_qs.filter(critico=False)

            crit_count = crit_qs.count()
            no_crit_count = no_crit_qs.count()

            # Si hay exactamente 1 reporte critico, guardo su pk
            single_crit_id = None
            if crit_count == 1:
                single_crit_id = crit_qs.first().pk

            # Lo mismo para no critico
            single_no_crit_id = None
            if no_crit_count == 1:
                single_no_crit_id = no_crit_qs.first().pk

            open_failures_dict[asset.pk] = {
                'crit_count': crit_count,
                'no_crit_count': no_crit_count,
                'single_crit_id': single_crit_id,
                'single_no_crit_id': single_no_crit_id,
            }

        context['open_failures_dict'] = open_failures_dict
        return context


@login_required
# @csrf_exempt
def AssetSummaryPDFView(request):
    """
    Genera un PDF que contiene:
      - Una primera página (resumen) con un “card” por cada activo seleccionado (de la lista del modal). Cada card muestra:
          • Nombre, código, supervisor, capitán, ubicación, indicador de cumplimiento y cantidad de reportes de falla abiertos.
          • Se dispondrán en 3 columnas (la plantilla se encargará de ello).
      - A continuación, para cada activo se listarán, en páginas siguientes, las órdenes de trabajo en ejecución (estado "x").
        Para cada OT se mostrarán las actividades (tareas) abiertas y las cerradas, así como, debajo, si existe un reporte de falla o una rutina asociada.
      - Finalmente, se listarán también los reportes de falla abiertos del activo, indicando si son críticos y el usuario que los generó.
      
    Toda la lógica se procesa en la vista para que la plantilla no tenga lógica.
    Se espera que el formulario del modal envíe, vía POST, una lista de activos seleccionados (por su “abbreviation”).
    """
    if request.method == "POST":
        # Obtenemos la lista de activos seleccionados (por ejemplo, enviados en el input name="assets")
        selected_asset_ids = request.POST.getlist("assets")
    else:
        selected_asset_ids = []

    # Filtramos los activos que se mostrarán (solo los seleccionados y que estén activos)
    assets = Asset.objects.filter(abbreviation__in=selected_asset_ids, show=True).order_by('name')

    asset_details = []
    for asset in assets:
        # Información básica
        supervisor_name = asset.supervisor.get_full_name() if asset.supervisor else "---"
        captain_name = asset.capitan.get_full_name() if asset.capitan else "---"
        location = asset.place.name if asset.place else "---"
        compliance = asset.maintenance_compliance_cache if asset.maintenance_compliance_cache is not None else 0

        # Reportes de falla abiertos (para este activo)
        open_failures = FailureReport.objects.filter(
            equipo__system__asset=asset,
            closed=False
        )

        failures_count = open_failures.count()
        failures_data = list(open_failures.values("id", "critico", "report", "description"))

        # Órdenes de trabajo en ejecución (estado "x")
        ots = Ot.objects.filter(system__asset=asset, state='x').order_by('creation_date')

        ot_details = []
        for ot in ots:
            tasks_open = list(ot.task_set.filter(finished=False).order_by('start_date'))
            tasks_closed = list(ot.task_set.filter(finished=True).order_by('start_date'))
            # Verificamos si la OT tiene un reporte de falla asociado (opcional, según tu modelo)
            ot_failure = ot.failure_report.filter(closed=False).first()
            # Verificamos si la OT tiene una rutina de mantenimiento asociada (esto puede variar según la relación)
            ot_rutina = ot.ruta_set.first()
            ot_details.append({
                "ot": ot,
                "tasks_open": tasks_open,
                "tasks_closed": tasks_closed,
                "failure": ot_failure,
                "rutina": ot_rutina,
            })

        asset_details.append({
            "asset": asset,
            "supervisor_name": supervisor_name,
            "captain_name": captain_name,
            "location": location,
            "compliance": compliance,
            "failures_count": failures_count,
            "failures_data": failures_data,
            "ots": ot_details,
        })

    context = {
        "selected_assets": asset_details,
        "today": date.today(),
    }
    return render_to_pdf("got/mantenimiento/asset_summary.html", context)


class AssetDetailView(LoginRequiredMixin, generic.DetailView):
    model = Asset
    template_name = 'got/assets/asset_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset = self.get_object()
        user = self.request.user
        systems = get_full_systems(asset, user)
        rotativos = Equipo.objects.filter(system__in=get_full_systems_ids(asset, user), tipo='r').exists()
        
        context['rotativos'] = rotativos
        context['view_type'] = 'detail'
        context['consumibles'] = Suministro.objects.filter(asset=asset).exists()
        context['page_obj'] = systems.order_by('name')
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
    template_name = 'got/assets/asset_maintenance_plan.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset = self.get_object()
        user = self.request.user
        filtered_rutas, current_month_name_es = get_filtered_rutas(asset, user, self.request.GET)

        # 2) Separamos rutinas con "ejecución"
        executing_rutas = []
        normal_rutas = []
        for r in filtered_rutas:
            if r.ot and r.ot.state == 'x':
                executing_rutas.append(r)
            else:
                normal_rutas.append(r)

        # 3) Guardamos en contexto
        context['rotativos'] = Equipo.objects.filter(system__in=get_full_systems_ids(asset, user), tipo='r').exists()
        context['view_type'] = 'rutas'
        context['asset'] = asset
        context['mes'] = current_month_name_es

        # Rutinas "no en ejecución"
        context['page_obj_rutas'] = normal_rutas

        # Rutinas en ejecución
        context['exec_rutas'] = executing_rutas
        context['rutinas_filter_form'] = RutinaFilterForm(self.request.GET or None, asset=asset)
        context['rutinas_disponibles'] = Ruta.objects.filter(system__asset=asset)

        # Ubicaciones => definimos r.ubic_label, etc.
        ubicaciones = set()
        for r in filtered_rutas:
            if r.equipo and r.equipo.ubicacion:
                ubicaciones.add(r.equipo.ubicacion)

            # Asignar r.ubic_label = su ubicación o "(sin)"
            if r.equipo and r.equipo.ubicacion:
                r.ubic_label = r.equipo.ubicacion
            else:
                r.ubic_label = "(sin)"

        context['ubicaciones_unicas'] = sorted(ubicaciones)
        return context

    def post(self, request, *args, **kwargs):
        if 'download_excel' in request.POST:
            return self.export_rutinas_to_excel(request.POST)
        else:
            return redirect(request.path)

    def export_rutinas_to_excel(self, request_data):
        asset = self.get_object()
        user = self.request.user
        filtered_rutas, _ = get_filtered_rutas(asset, user, request_data)
        headers = [
            'Equipo', 'Ubicación', 'Código', 'Frecuencia', 'Control', 'Tiempo Restante',
            'Última Intervención', 'Próxima Intervención', 'Orden de Trabajo', 'Actividad', 'Responsable'
        ]
        data = []

        for ruta in filtered_rutas:
            days_left = (ruta.next_date - datetime.now().date()).days if ruta.next_date else '---'
            data.append([
                ruta.equipo.name if ruta.equipo else ruta.system.name,
                ruta.equipo.system.location if ruta.equipo else ruta.system.location,
                ruta.name,
                ruta.frecuency,
                ruta.get_control_display(),
                days_left,
                ruta.intervention_date.strftime('%d/%m/%Y') if ruta.intervention_date else '---',
                ruta.next_date.strftime('%d/%m/%Y') if ruta.next_date else '---',
                ruta.ot.num_ot if ruta.ot else '---',
                '---',
                ''
            ])

            tasks = Task.objects.filter(ruta=ruta)
            for task in tasks:
                responsable_name = task.responsible.get_full_name() if task.responsible else '---'
                data.append(['', '', '', '', '', '', '', '', '', f'- {task.description}', responsable_name])

        filename = 'rutinas.xlsx'
        table_title = 'Reporte de Rutinas'
        return pro_export_to_excel(model=Ruta, headers=headers, data=data, filename=filename, table_title=table_title)


class AssetDocumentsView(View):
    form_class = DocumentForm
    template_name = 'got/assets/add-document.html'

    def get_context_data(self, request, asset, form=None, keyword=None):
        systems = asset.system_set.all()
        ots = Ot.objects.filter(system__in=systems)
        equipos = Equipo.objects.filter(system__in=systems)
        all_docs = Document.objects.filter( Q(asset=asset) | Q(ot__in=ots) | Q(equipo__in=equipos)).distinct()

        if keyword:
            all_docs = all_docs.filter(description__icontains=keyword)

        paginator = Paginator(all_docs, 30)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        today = date.today()
        for doc in page_obj:
            doc.is_expired = False
            if doc.date_expiry and doc.date_expiry < today:
                doc.is_expired = True

        existing_tags = Tag.objects.annotate(num_docs=Count('taggit_taggeditem_items')).filter(num_docs__gt=0).order_by('name')
        if form is None:
            form = self.form_class()

        context = {
            'asset': asset,
            'documents': page_obj,
            'form': form,
            'today': today,
            'is_paginated': page_obj.has_other_pages(),
            'page_obj': page_obj,
            'existing_tags': existing_tags,
            'request': request  
        }
        return context

    def get(self, request, abbreviation):
        asset = get_object_or_404(Asset, abbreviation=abbreviation)
        keyword = request.GET.get('keyword', '').strip()
        context = self.get_context_data(request, asset, keyword=keyword)
        return render(request, self.template_name, context)

    def post(self, request, abbreviation):
        asset = get_object_or_404(Asset, abbreviation=abbreviation)
        form = self.form_class(request.POST, request.FILES)
        form.instance.asset = asset
        if form.is_valid():
            document = form.save(commit=False)
            document.asset = asset
            document.uploaded_by = request.user
            document.save()
            form.save_m2m()
            return redirect('got:asset-documents', abbreviation=abbreviation)
        else:
            messages.error(request, 'Error al agregar el documento. Por favor, revisa los campos.')
            keyword = request.GET.get('keyword', '').strip()
            context = self.get_context_data(request, asset, form=form, keyword=keyword)
            return render(request, self.template_name, context)


@login_required
def edit_document(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    if request.method == 'POST':
        form = DocumentEditForm(request.POST, instance=doc)
        if form.is_valid():
            form.save()
            if doc.asset:
                abbr = doc.asset.abbreviation
            elif doc.ot:
                abbr = doc.ot.system.asset.abbreviation
            else:
                abbr = doc.equipo.system.asset.abbreviation
            return redirect('got:asset-documents', abbreviation=abbr)
    if doc.asset:
        abbr = doc.asset.abbreviation
    elif doc.ot:
        abbr = doc.ot.system.asset.abbreviation
    elif doc.equipo:
        abbr = doc.equipo.system.asset.abbreviation
    return redirect('got:asset-documents', abbreviation=abbr)


@login_required
def delete_document(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    if request.method == 'POST':
        if doc.asset:
            abbr = doc.asset.abbreviation
        elif doc.ot:
            abbr = doc.ot.system.asset.abbreviation
        elif doc.equipo:
            abbr = doc.equipo.system.asset.abbreviation
        doc.delete()
        return redirect('got:asset-documents', abbreviation=abbr)
    return redirect('got:asset-documents', abbreviation='AAA')


'SYSTEMS VIEW'
class SysDetailView(LoginRequiredMixin, generic.DetailView):
    model = System
    template_name = "got/systems/system_base.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        system = self.get_object()

        # Aquí se añade la lógica para el parámetro de retorno ("next")
        next_url = self.request.GET.get('next')
        if not next_url:
            # Si no se pasó, se redirige por defecto a la vista de detalle del asset del sistema
            next_url = reverse('got:asset-detail', args=[system.asset.abbreviation])
        context['next_url'] = next_url

        main_equipos = Equipo.objects.filter(system=system, related__isnull=True)
        # Para cada equipo, obtenemos sus dependientes
        equipos_con_dependientes = []
        for eq in main_equipos:
            dependientes = eq.related_with.all()
            equipos_con_dependientes.append({'principal': eq, 'dependientes': dependientes,})
        context['equipos_con_dependientes'] = equipos_con_dependientes

        rutinas = Ruta.objects.filter(system=system).order_by('-nivel', 'frecuency')
        context['rutinas'] = rutinas
        # context['items'] = Item.objects.all()
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
    template_name = 'got/systems/system_confirm_delete.html'

    def delete(self, request, *args, **kwargs):
        system = self.get_object()
        system.modified_by = request.user
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        asset_code = self.object.asset.abbreviation
        success_url = reverse_lazy(
            'got:asset-detail', kwargs={'pk': asset_code})
        return str(success_url)
    

class EquipoDetailView(LoginRequiredMixin, generic.DetailView):
    model = Equipo
    template_name = "got/systems/equipo_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        equipo = self.get_object()
        system = equipo.system
        
        # Menú lateral de equipos: todos los equipos principales del sistema y sus dependientes
        main_equipos = Equipo.objects.filter(system=system, related__isnull=True)
        equipos_con_dependientes = []
        for eq in main_equipos:
            dependientes = eq.related_with.all()
            equipos_con_dependientes.append({
                'principal': eq,
                'dependientes': dependientes,
            })
        context['equipos_con_dependientes'] = equipos_con_dependientes
        context['object'] = equipo
        context['suministros'] = Suministro.objects.filter(equipo=equipo)
        context['rutinas'] = Ruta.objects.filter(equipo=equipo)
        context['transferencias'] = Transferencia.objects.filter(equipo=equipo)
        return context

    def get_success_url(self):
        return reverse('got:equipo-detail', args=[self.object.code])


@login_required
def reportHoursAsset(request, asset_id):
    asset = get_object_or_404(Asset, pk=asset_id)
    today = date.today()
    dates = [today - timedelta(days=x) for x in range(90)]
    systems = get_full_systems_ids(asset, request.user)
    equipos_rotativos = Equipo.objects.filter(system__in=systems, tipo='r')
    rotativos = equipos_rotativos.exists()

    # --------------------------------------------------------------------------------------
    # 1. Verificar si es un POST del "modal" o el "formulario tradicional"
    # --------------------------------------------------------------------------------------
    if request.method == 'POST':
        # Si en el POST vienen "equipo_id" y "report_date" y "hour",
        # asumimos que es el envío desde el modal de actualización.
        if "equipo_id" in request.POST and "report_date" in request.POST and "hour" in request.POST:
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
                return redirect(request.META.get(
                    'HTTP_REFERER',
                    reverse('got:horas-asset', args=[asset_id])
                ))
            
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

        else:
            # =============== LÓGICA DEL FORMULARIO TRADICIONAL ===============
            form = ReportHoursAsset(request.POST, equipos=equipos_rotativos, asset=asset)
            if form.is_valid():
                instance = form.save(commit=False)
                instance.reporter = request.user
                instance.modified_by = request.user
                instance.save()
                messages.success(request, "Formulario enviado correctamente.")
                return redirect(reverse('got:horas-asset', args=[asset_id]))
            else:
                # El form no es válido, se re-renderiza con errores
                messages.error(request, "Error en el formulario tradicional.")

    else:
        # GET: Simplemente creamos la instancia vacía del formulario tradicional
        form = ReportHoursAsset(equipos=equipos_rotativos, asset=asset)

    # --------------------------------------------------------------------------
    # 2. Construir la información (equipos_data y transposed_data) para la tabla
    # --------------------------------------------------------------------------
    hours = HistoryHour.objects.filter(component__system__asset=asset)[:90]

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
        registros = HistoryHour.objects.filter(
            component=equipo,
            report_date__range=(dates[-1], today)
        ).select_related('reporter')

        for reg in registros:
            if reg.report_date in horas_reportadas:
                horas_reportadas[reg.report_date]['hour'] = reg.hour
                horas_reportadas[reg.report_date]['reporter'] = (
                    reg.reporter.username if reg.reporter else None
                )
                horas_reportadas[reg.report_date]['hist_id'] = reg.id

        # Crear lista en el mismo orden que `dates`
        lista_horas = [horas_reportadas[d] for d in dates]

        equipos_data.append({
            'equipo': equipo,
            'horas': lista_horas,
        })

    # Transponer la data (filas=fechas, columnas=equipos)
    transposed_data = []
    for i, d in enumerate(dates):
        fila = {
            'date': d,
            'valores': []
        }
        for data in equipos_data:
            fila['valores'].append(data['horas'][i])
        transposed_data.append(fila)

    # --------------------------------------------------------------------------
    # 3. Renderizar la plantilla
    # --------------------------------------------------------------------------
    context = {
        'form': form,  # el formulario tradicional, sea vacío o con errores
        'horas': hours,
        'asset': asset,
        'equipos_data': equipos_data,
        'equipos_rotativos': equipos_rotativos,
        'dates': dates,
        'transposed_data': transposed_data,
        'rotativos': rotativos
    }
    return render(request, 'got/assets/hours_asset.html', context)


class RutaDetailView(LoginRequiredMixin, generic.DetailView):
    model = Ruta
    template_name = 'got/rutinas/ruta_detail.html'
    context_object_name = 'ruta'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ruta = self.get_object()

        all_items = Item.objects.all()
        all_services = Service.objects.all()
        context['all_items'] = all_items
        context['all_services'] = all_services
        context['tasks'] = ruta.task_set.all().order_by('-priority')
        requirements = ruta.requisitos.all()
        art_requirements = []
        svc_requirements = []
        material_types = ['m', 'h']

        for req in requirements:
            if req.tipo in material_types:
                if req.item:
                    name = str(req.item)
                else:
                    name = str(req.descripcion)
                art_requirements.append((name.lower(), req))
            elif req.tipo == 's':
                if req.service:
                    name = req.service.description.lower()
                else:
                    name = str(req.descripcion).lower()
                svc_requirements.append((name, req))

        art_requirements.sort(key=lambda x: x[0])
        svc_requirements.sort(key=lambda x: x[0])

        art_requirements = [req for _, req in art_requirements]
        svc_requirements = [req for _, req in svc_requirements]

        context['requirements_art'] = art_requirements
        context['requirements_svc'] = svc_requirements
        context['task_form'] = RutActForm(asset=ruta.system.asset)
        context['requirement_form'] = MaintenanceRequirementForm()
        context['service_form'] = ServiceForm()
        context['activity_logs'] = ActivityLog.objects.filter(model_name='Ruta', object_id=str(ruta.code)).order_by('-timestamp')
        context['task_edit_forms'] = {task.id: RutActForm(instance=task, asset=ruta.system.asset) for task in ruta.task_set.all()}
        context['requirement_edit_forms'] = {req.id: MaintenanceRequirementForm(instance=req) for req in requirements}
        context['material_types'] = material_types
        return context

    def post(self, request, *args, **kwargs):
        ruta = self.get_object()
        self.object = ruta
        action = request.POST.get('action')

        if action == 'create_task':
            task_form = RutActForm(request.POST, asset=ruta.system.asset)
            if task_form.is_valid():
                task = task_form.save(commit=False)
                task.ruta = ruta
                task.finished = False
                task.modified_by = request.user
                task.save()
                messages.success(request, 'Actividad creada exitosamente.')
                return redirect('got:ruta_detail', pk=ruta.pk)
            else:
                messages.error(request, 'Error al crear la actividad.')
                context = self.get_context_data()
                context['task_form'] = task_form
                return render(request, self.template_name, context)

        elif action == 'edit_task':
            task_id = request.POST.get('task_id')
            task = get_object_or_404(Task, id=task_id, ruta=ruta)
            task_form = RutActForm(request.POST, instance=task, asset=ruta.system.asset)
            if task_form.is_valid():
                task = task_form.save(commit=False)
                task.modified_by = request.user
                task.save()
                messages.success(request, 'Actividad actualizada exitosamente.')
            else:
                messages.error(request, 'Error al actualizar la actividad.')
            return redirect('got:ruta_detail', pk=ruta.pk)

        elif action == 'delete_task':
            task_id = request.POST.get('task_id')
            task = get_object_or_404(Task, id=task_id, ruta=ruta)
            task.delete()
            messages.success(request, 'Actividad eliminada exitosamente.')
            return redirect('got:ruta_detail', pk=ruta.pk)

        elif action == 'create_requirement':
            requirement_form = MaintenanceRequirementForm(request.POST)
            if requirement_form.is_valid():
                requirement = requirement_form.save(commit=False)
                requirement.ruta = ruta
                requirement.modified_by = request.user
                requirement.save()
                messages.success(request, 'Requerimiento creado exitosamente.')
                return redirect('got:ruta_detail', pk=ruta.pk)
            else:
                for field, errors in requirement_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
                messages.error(request, 'Error al crear el requerimiento.')
                context = self.get_context_data()
                context['requirement_form'] = requirement_form
                return render(request, self.template_name, context)

        elif action == 'edit_requirement':
            requirement_id = request.POST.get('requirement_id')
            requirement = get_object_or_404(MaintenanceRequirement, id=requirement_id, ruta=ruta)
            requirement_form = MaintenanceRequirementForm(request.POST, instance=requirement)
            if requirement_form.is_valid():
                requirement = requirement_form.save(commit=False)
                requirement.modified_by = request.user
                requirement.save()
                messages.success(request, 'Requerimiento actualizado exitosamente.')
            else:
                messages.error(request, 'Error al actualizar el requerimiento.')
            return redirect('got:ruta_detail', pk=ruta.pk)

        elif action == 'delete_requirement':
            requirement_id = request.POST.get('requirement_id')
            requirement = get_object_or_404(MaintenanceRequirement, id=requirement_id, ruta=ruta)
            requirement.delete()
            messages.success(request, 'Requerimiento eliminado exitosamente.')
            return redirect('got:ruta_detail', pk=ruta.pk)

        elif action == 'create_service':
            service_form = ServiceForm(request.POST)
            if service_form.is_valid():
                service_form.save()
                messages.success(request, 'Servicio creado exitosamente.')
            else:
                for field, errors in service_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
                messages.error(request, 'Error al crear el servicio.')
            return redirect('got:ruta_detail', pk=ruta.pk)

        else:
            messages.error(request, 'Acción no reconocida.')
            return redirect('got:ruta_detail', pk=ruta.pk)


class RutaCreate(CreateView):
    model = Ruta
    form_class = RutaForm
    template_name = 'got/rutinas/ruta_form.html'

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
    template_name = 'got/rutinas/ruta_form.html'

    def form_valid(self, form):
        form.instance.modified_by = self.request.user 
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['system'] = self.object.system
        return kwargs


class RutaDelete(DeleteView):
    model = Ruta
    template_name = 'got/rutinas/ruta_confirm_delete.html'

    def get_success_url(self):
        sys_code = self.object.system.id
        success_url = reverse_lazy('got:sys-detail', kwargs={'pk': sys_code})
        return success_url


def acta_entrega_pdf(request, pk):
    equipo = get_object_or_404(Equipo, pk=pk)
    current_date = timezone.localdate()
    context = {
        'equipo': equipo,
        'current_date': current_date,
    }
    return render_to_pdf('got/systems/acta-entrega.html', context)
    

def asset_maintenance_pdf(request, asset_id):
    """
    Vista para generar un PDF con la información de todos los sistemas de un activo.
    """
    asset = get_object_or_404(Asset, pk=asset_id)
    systems = System.objects.filter(asset=asset).prefetch_related(
        'equipos',
        'rutas__requisitos',
        'ot_set'
    )
    start_date = timezone.now()

    sections = [
        {'title': 'Resumen', 'id': 'summary'},
        {'title': 'Información de los Sistemas', 'id': 'systems-info'},
        {'title': 'Equipos Asociados', 'id': 'associated-equipment'},
        {'title': 'Rutinas de Mantenimiento', 'id': 'maintenance-routines'},
        {'title': 'Bitácora de Mantenimientos', 'id': 'maintenance-log'},
    ]

    context = {
        'asset': asset,
        'systems': systems,
        'sections': sections,
        'current_date': start_date,
    }

    return render_to_pdf('got/systems/asset_pdf_template.html', context)


class EquipoCreateView(LoginRequiredMixin, CreateView):
    model = Equipo
    form_class = EquipoForm
    template_name = 'got/systems/equipo_form.html'
    http_method_names = ['get', 'post']

    def dispatch(self, request, *args, **kwargs):
        # Guarda la URL previa si está presente para redirigir luego
        self.next_url = request.GET.get('next') or request.POST.get('next') or ''
        return super().dispatch(request, *args, **kwargs)

    def get_system(self):
        # Recupera el sistema utilizando el parámetro 'pk' de la URL
        return get_object_or_404(System, pk=self.kwargs['pk'])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Se inyecta el objeto system en los argumentos del formulario
        kwargs['system'] = self.get_system()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Se instancia el formulario de carga de imágenes
        if self.request.POST:
            context['upload_form'] = UploadImages(self.request.POST, self.request.FILES)
        else:
            context['upload_form'] = UploadImages()
        context['sys'] = self.get_system()
        return context

    def post(self, request, *args, **kwargs):
        self.object = None  # Asegurarse de que self.object esté inicializado
        form = self.get_form()
        upload_form = UploadImages(request.POST, request.FILES)
        # Se validan ambos formularios
        if form.is_valid() and upload_form.is_valid():
            return self.form_valid(form, upload_form)
        else:
            return self.form_invalid(form, upload_form)

    def form_valid(self, form, upload_form):
        system = self.get_system()
        form.instance.system = system
        asset_abbreviation = system.asset.abbreviation
        # Convertir el tipo a mayúsculas (suponiendo que es requerido)
        tipo = form.cleaned_data['tipo'].upper()

        try:
            with transaction.atomic():
                # Generar código único para el equipo
                form.instance.code = generate_equipo_code(asset_abbreviation, tipo)
                form.instance.modified_by = self.request.user
                # Guarda el registro del equipo; esto asigna self.object
                response = super().form_valid(form)
        except IntegrityError:
            form.add_error('code', 'Error al generar un código único. Por favor, inténtalo de nuevo.')
            return self.form_invalid(form, upload_form)

        # Una vez guardado el equipo, se procesan las imágenes
        for file in self.request.FILES.getlist('file_field'):
            Image.objects.create(image=file, equipo=self.object)
        messages.success(self.request, "Equipo creado exitosamente.")
        return response

    def form_invalid(self, form, upload_form):
        context = self.get_context_data(form=form, upload_form=upload_form)
        return self.render_to_response(context)

    def get_success_url(self):
        """
        Redirige a la URL 'next' si está presente; de lo contrario redirige a la vista de detalle del sistema.
        """
        if self.next_url:
            return self.next_url
        else:
            return reverse('got:sys-detail', kwargs={'pk': self.object.system.pk})


class EquipoUpdate(UpdateView):
    model = Equipo
    form_class = EquipoForm
    template_name = 'got/systems/equipo_form.html'
    http_method_names = ['get', 'post']

    def dispatch(self, request, *args, **kwargs):
        # Guardar la URL previa en self.next_url, si la hay
        self.next_url = request.GET.get('next') or request.POST.get('next') or ''
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        equipo = Equipo.objects.get(pk=self.kwargs['pk'])
        kwargs['system'] = get_object_or_404(System, equipos=equipo)
        return kwargs
    
    def get_object(self, queryset=None):
        """
        Sobrescribimos get_object para almacenar el tipo y code ANTES de que el form 
        actualice la instancia.
        """
        obj = super().get_object(queryset)
        # Guardar en atributos de la vista (self) los valores "viejos"
        self.old_tipo = obj.tipo  
        self.old_code = obj.code
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Formulario para carga de imágenes
        if self.request.POST:
            context['upload_form'] = UploadImages(self.request.POST, self.request.FILES)
        else:
            context['upload_form'] = UploadImages()
        # Formset para mostrar las imágenes ya asociadas al equipo
        ImageFormset = modelformset_factory(Image, fields=('image',), extra=0)
        context['image_formset'] = ImageFormset(queryset=self.object.images.all())
        # Agregar la cantidad de imágenes
        context['image_count'] = self.object.images.count()
        context['next_url'] = self.next_url
        return context
    
    def form_valid(self, form):

        form.instance.modified_by = self.request.user
        response = super().form_valid(form)

        new_tipo = self.object.tipo  # el "tipo" que el usuario seleccionó 
        new_code = self.object.code 

        if new_tipo != self.old_tipo:
            # Llamar a la función update_equipo_code con el code viejo
            update_equipo_code(self.old_code)
            messages.info(
                self.request, 
                f"El tipo cambió de '{self.old_tipo}' a '{new_tipo}'. Se actualizó el código del equipo."
            )
        
        upload_form = self.get_context_data()['upload_form']
        if upload_form.is_valid():
            for file in self.request.FILES.getlist('file_field'):
                Image.objects.create(image=file, equipo=self.object)
                print(file)
        return response
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Opción para eliminar imagen vía formulario tradicional (fallback)
        if "delete_image" in request.POST:
            image_id = request.POST.get("delete_image")
            Image.objects.filter(id=image_id, equipo=self.object).delete()
            return redirect(self.get_success_url())
        return super().post(request, *args, **kwargs)
    
    def get_success_url(self):
        """
        Si existe la self.next_url, redirige allí.
        De lo contrario, comportarse como antes (por ejemplo, al System detail).
        """
        if self.next_url:
            return self.next_url
        else:
            # fallback
            sys_code = self.object.system.id
            return reverse_lazy('got:sys-detail', kwargs={'pk': sys_code})


class EquipoDeleteImageView(LoginRequiredMixin, View):
    def post(self, request, pk):
        # Obtener el Equipo
        equipo = get_object_or_404(Equipo, pk=pk)
        # Obtener el ID de la imagen desde el POST
        image_id = request.POST.get('image_id')
        if not image_id:
            return JsonResponse({'error': 'No se proporcionó el ID de la imagen.'}, status=400)
        
        # Obtener la imagen y asegurarse de que pertenece al equipo
        image = get_object_or_404(Image, id=image_id, equipo=equipo)
        
        # Eliminar la imagen
        image.delete()
        
        # Devolver la cantidad actualizada de imágenes
        image_count = equipo.images.count()
        return JsonResponse({'success': True, 'image_count': image_count})


class EquipoDelete(DeleteView):
    model = Equipo
    template_name = 'got/systems/equipo_confirm_delete.html'

    def dispatch(self, request, *args, **kwargs):
        # Capturar la next_url
        self.next_url = request.GET.get('next') or ''
        return super().dispatch(request, *args, **kwargs)
    
    def get_success_url(self):
        # Redirigir a next si existe
        if self.next_url:
            return self.next_url
        # fallback
        sys_code = self.object.system.id
        return reverse_lazy('got:sys-detail', kwargs={'pk': sys_code})


def add_supply_to_equipment(request, code):
    equipo = get_object_or_404(Equipo, code=code)
    if request.method == 'POST':
        form = SuministrosEquipoForm(request.POST)
        if form.is_valid():
            suministro = form.save(commit=False)
            suministro.equipo = equipo
            suministro.save()
            return redirect(reverse('got:sys-detail', args=[equipo.system.id, equipo.code]))


'FAILURE REPORTS VIEW'
class FailureListView(LoginRequiredMixin, generic.ListView):
    model = FailureReport
    paginate_by = 15
    template_name = 'got/fail/failurereport_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['assets'] = Asset.objects.filter(show=True)
        context['count_proceso'] = self.get_queryset().filter(closed=False, related_ot__isnull=False).count()
        context['count_abierto'] = self.get_queryset().filter(closed=False).count()
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        asset_id = self.request.GET.get('asset_id')
        state = self.request.GET.get('state')
        user = self.request.user

        if asset_id:
            queryset = queryset.filter(equipo__system__asset_id=asset_id)

        if state == 'abierto':
            queryset = queryset.filter(closed=False, related_ot__isnull=True)
        elif state == 'proceso':
            queryset = queryset.filter(closed=False, related_ot__isnull=False)
        elif state == 'cerrado':
            queryset = queryset.filter(closed=True)

        if self.request.user.groups.filter(name='maq_members').exists():
            supervised_assets = Asset.objects.filter(Q(supervisor=user) | Q(capitan=user))
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
        system = failurereport.equipo.system
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
        email_template_name = 'emails/failure_report_email.txt'
        
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
        if 'related_ot' in form.cleaned_data:
            form.instance.related_ot = form.cleaned_data['related_ot']
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
        if ot.state == 'f':
            fail.closed = True
        fail.save()

        return redirect('got:failure-report-detail', pk=fail_id)
    else:
        return redirect('got:failure-report-detail', pk=fail_id)


'OTS VIEWS'
class OtListView(LoginRequiredMixin, generic.ListView):
    model = Ot
    paginate_by = 16
    template_name = 'got/ots/ot_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        asset_id = self.request.GET.get('asset_id')
        if asset_id:
            systems = System.objects.filter(asset_id=asset_id)
            context['systems'] = systems
            context['selected_asset_id'] = asset_id
        else:
            context['systems'] = System.objects.none()
            context['selected_asset_id'] = None

        user = self.request.user
        user_groups = user.groups.values_list('name', flat=True)

        if 'buzos_members' in user_groups:
            info_filter = Asset.objects.filter(area='b', show=True)
        elif 'maq_members' in user_groups:
            info_filter = Asset.objects.none() 
        else:
            info_filter = Asset.objects.filter(show=True)
        context['asset'] = info_filter

        super_group = Group.objects.get(name='super_members')
        users_in_group = super_group.user_set.all()
        context['super_members'] = users_in_group

        queryset = self.get_queryset()
        total_ots_en_ejecucion = queryset.filter(state='x').count()
        context['total_ots_en_ejecucion'] = total_ots_en_ejecucion

        return context

    def get_queryset(self):
        queryset = Ot.objects.all().select_related('system', 'system__asset')

        user = self.request.user
        user_groups = user.groups.values_list('name', flat=True)

        if 'maq_members' in user_groups:
            supervised_assets = Asset.objects.filter(Q(supervisor=user) | Q(capitan=user))
            queryset = queryset.filter(system__asset__in=supervised_assets)
        elif 'buzos_members' in user_groups:
            supervised_assets = Asset.objects.filter(area='b')
            queryset = queryset.filter(system__asset__in=supervised_assets)
        elif any(group in user_groups for group in ['super_members', 'serport_members', 'gerencia', 'operaciones']):
            pass
        else:
            queryset = queryset.none()

        state = self.request.GET.get('state')
        asset_id = self.request.GET.get('asset_id')
        responsable = self.request.GET.get('responsable')
        num_ot = self.request.GET.get('num_ot')
        system_id = self.request.GET.get('system_id')
        keyword = self.request.GET.get('keyword')

        if state:
            queryset = queryset.filter(state=state)
        if asset_id:
            queryset = queryset.filter(system__asset_id=asset_id)
        if responsable:
            queryset = queryset.filter(supervisor__icontains=responsable)
        if num_ot:
            queryset = queryset.filter(num_ot=num_ot)
        if system_id:
            queryset = queryset.filter(system_id=system_id)
        if keyword:
            queryset = queryset.filter(description__icontains=keyword)

        queryset = queryset.annotate(
            unfinished_tasks=Count('task', filter=Q(task__finished=False)),
            is_pausado=Case(
                When(Q(state='x') & Q(unfinished_tasks=0), then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
            state_order=Case(
                When(state='x', then=1),            # En ejecución
                When(is_pausado=True, then=2),      # Pausado
                When(state='a', then=3),            # Abierto
                When(state='f', then=4),            # Finalizado
                When(state='c', then=5),            # Cancelado
                default=6,
                output_field=IntegerField(),
            )
        ).order_by('state_order', '-creation_date', '-num_ot')

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
    template_name = 'got/ots/ot_form.html'

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
    template_name = 'got/ots/ot_form.html'

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
        ot.modified_by = self.request.user
        ot.save()
        return super().form_valid(form)


class OtDelete(DeleteView):
    model = Ot
    success_url = reverse_lazy('got:ot-list')
    template_name = 'got/ots/ot_confirm_delete.html'


def ot_pdf(request, num_ot):
    ot_info = get_object_or_404(Ot, num_ot=num_ot)
    rutas = Ruta.objects.filter(ot=ot_info)
    rutina = rutas.exists()
    fallas = FailureReport.objects.filter(related_ot=ot_info)
    failure = fallas.exists()

    tareas = Task.objects.filter(ot=ot_info).select_related('responsible', 'responsible__profile').order_by('start_date')
    usuarios_participacion_dict = {}

    for tarea in tareas:
        if tarea.responsible:
            user = tarea.responsible
            if user.id not in usuarios_participacion_dict:
                usuarios_participacion_dict[user.id] = {
                    'nombre': f"{user.first_name} {user.last_name}",
                    'cargo': user.profile.cargo if hasattr(user, 'profile') else '',
                    'earliest_start_date': tarea.start_date,
                    'latest_final_date': tarea.final_date,
                }
            else:
                # Actualizar earliest_start_date
                if tarea.start_date and (usuarios_participacion_dict[user.id]['earliest_start_date'] is None or tarea.start_date < usuarios_participacion_dict[user.id]['earliest_start_date']):
                    usuarios_participacion_dict[user.id]['earliest_start_date'] = tarea.start_date
                # Actualizar latest_final_date
                if tarea.final_date and (usuarios_participacion_dict[user.id]['latest_final_date'] is None or tarea.final_date > usuarios_participacion_dict[user.id]['latest_final_date']):
                    usuarios_participacion_dict[user.id]['latest_final_date'] = tarea.final_date
    

    usuarios_participacion = []
    for user_id, info in usuarios_participacion_dict.items():
        if info['earliest_start_date'] and info['latest_final_date']:
            total_execution_time = info['latest_final_date'] - info['earliest_start_date']
            total_execution_time_display = f"{total_execution_time.days} días"
        else:
            total_execution_time_display = "N/A"
        
        usuarios_participacion.append({
            'nombre': info['nombre'],
            'cargo': info['cargo'],
            'start_date': info['earliest_start_date'],
            'final_date': info['latest_final_date'],
            'total': total_execution_time_display
        })

    images_qs = Image.objects.filter(task__ot=ot_info)
    has_evidence = images_qs.exists()
    
    # Obtener una lista de todas las URLs de las imágenes
    evidence_images = [image.image.url for image in images_qs]
    context = {
        'ot': ot_info,
        'fallas': fallas,
        'failure': failure,
        'rutas': rutas,
        'rutina': rutina,
        'users': usuarios_participacion,
        'has_evidence': has_evidence,
        'evidence_images': evidence_images,
        'tareas': tareas
    }
    template_path = 'got/ots/ot_pdf.html'
    download = request.GET.get('download', None)
    response = render_to_pdf(template_path, context)
    filename = f'orden_de_trabajo_{num_ot}.pdf'
    if download:
        content = f'attachment; filename="{filename}"'
    else:
        content = f'inline; filename="{filename}"'
    response['Content-Disposition'] = content
    return response


from django.db.models import Func

class DayInterval(Func):
    template = "(%(expressions)s * interval '1 day')"


'TASKS VIEW'
class AssignedTaskByUserListView(LoginRequiredMixin, generic.ListView):
    model = Task
    template_name = 'got/ots/tasks_pendient.html'
    paginate_by = 25

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['assets'] = Asset.objects.all()
        context['all_users'] = operational_users(self.request.user)
        context['total_tasks'] = self.get_queryset().count()

        # Incluimos los parámetros de fecha para poder construir el enlace al PDF
        context['start_date'] = self.request.GET.get('start_date', '')
        context['end_date'] = self.request.GET.get('end_date', '')
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

        # Filtrado por rango de fechas (solapamiento)
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                queryset = queryset.annotate(
                    calc_final_date=ExpressionWrapper(
                        F('start_date') + DayInterval(F('men_time')),
                        output_field=DateField()
                    )
                ).filter(calc_final_date__gte=start_date, start_date__lte=end_date)
            except ValueError:
                pass  # Si hay error en el formato, no filtramos por fecha

        if current_user.groups.filter(name='serport_members').exists():
            return queryset.filter(responsible=current_user)
        elif current_user.groups.filter(name='super_members').exists():
            return queryset
        elif current_user.groups.filter(name_in=['maq_members', 'buzos_members']).exists():
            return queryset.filter(ot__system__asset__supervisor=current_user)
        return queryset.none() 
    

@login_required
def assignedTasks_pdf(request):
    queryset = Task.objects.filter(ot__isnull=False, start_date__isnull=False, finished=False).order_by('start_date')

    asset_id = request.GET.get('asset_id')
    if asset_id:
        queryset = queryset.filter(ot__system__asset_id=asset_id)

    responsable_id = request.GET.get('worker')
    if responsable_id:
        queryset = queryset.filter(responsible=responsable_id)

    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            queryset = queryset.annotate(
                calc_final_date=ExpressionWrapper(
                    F('start_date') + DayInterval(F('men_time')),
                    output_field=DateField()
                )
            ).filter(calc_final_date__gte=start_date, start_date__lte=end_date)
        except ValueError:
            pass

    current_user = request.user
    if current_user.groups.filter(name='serport_members').exists():
        queryset = queryset.filter(responsible=current_user)
    elif current_user.groups.filter(name='super_members').exists():
        pass
    elif current_user.groups.filter(name='maq_members').exists():
        queryset = queryset.filter(ot__system__asset__supervisor=current_user)
    elif current_user.groups.filter(name='buzos_members').exists():
        user_station = current_user.profile.station
        if user_station:
            queryset = queryset.filter(ot__system__asset__area='b', ot__system__location__in=user_station)
        else:
            queryset = queryset.filter(ot__system__asset__area='b')
    else:
        queryset = queryset.none()

    context = {'tasks': queryset}
    return render_to_pdf('got/ots/assigned_tasks_pdf.html', context)


class TaskCreate(CreateView):
    model = Task
    http_method_names = ['get', 'post']
    form_class = RutActForm
    template_name = 'got/ots/task_form.html'

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
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        ruta = get_object_or_404(Ruta, pk=self.kwargs['pk'])
        asset = ruta.system.asset  # Obtenemos el asset desde la ruta
        kwargs['asset'] = asset
        return kwargs


class TaskUpdate(UpdateView):
    model = Task
    template_name = 'got/ots/task_form.html'
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
    
    def get_success_url(self):
        task = self.object
        if task.ot:
            return reverse('got:ot-detail', kwargs={'pk': task.ot.num_ot})
        else:
            return reverse('got:my-tasks')


class TaskDelete(DeleteView):
    model = Task
    success_url = reverse_lazy('got:ot-list')
    template_name = 'got/ots/task_confirm_delete.html'


class TaskUpdaterut(UpdateView):
    model = Task
    form_class = RutActForm
    template_name = 'got/ots/task_form.html'
    http_method_names = ['get', 'post']

    def form_valid(self, form):
        form.instance.modified_by = self.request.user  # Asignar el usuario que modifica la tarea
        return super().form_valid(form)

    def get_success_url(self):
        sys_id = self.object.ruta.system.id
        return reverse_lazy('got:sys-detail', kwargs={'pk': sys_id})
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        task = get_object_or_404(Task, pk=self.kwargs['pk'])
        asset = task.ruta.system.asset
        kwargs['asset'] = asset
        return kwargs
    

class TaskDeleterut(DeleteView):
    model = Task
    def get_success_url(self):
        sys_id = self.object.ruta.system.id
        return reverse_lazy('got:sys-detail', kwargs={'pk': sys_id})

    def get(self, request, *args, **kwargs):
        context = {'task': self.get_object()}
        return render(request, 'got/ots/task_confirm_delete.html', context)


class Finish_task(UpdateView):
    model = Task
    form_class = FinishTask
    template_name = 'got/ots/task_finish_form.html'
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
    template_name = 'got/ots/task_finish_form.html'
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
    template_name = 'got/ots/task_reschedule.html'
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
    return render(request, 'got/rutinas/ruta_list.html', context)


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

    return render(request, 'got/rutinas/ruta_ot_form.html', 
                  {'formset_data': formset_data, 'ruta': ruta, 'dependencias': dependencias, 'fecha_seleccionada': fecha_seleccionada}
                  )


'OPERATIONS VIEW'
def OperationListView(request):
    assets = Asset.objects.filter(area='a', show=True)

    today = timezone.now().date()
    show_past = request.GET.get('show_past', 'false').lower() == 'true'
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
    paginator = Paginator(operaciones_list, 40)  # Mostrar 10 operaciones por página

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
    template_name = 'got/operations/operation_confirm_delete.html'



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

        user = self.request.user
        user_groups = set(user.groups.values_list('name', flat=True))
        context['user_groups'] = user_groups

        group_default_dpto = {
            'super_members': 'm',  # Mantenimiento
            'operaciones': 'o'     # Operaciones
        }

        default_dpto = ''
        for group, dpto in group_default_dpto.items():
            if group in user_groups:
                default_dpto = dpto
                break 

        dpto = self.request.GET.get('dpto', default_dpto)
        current_dpto = dpto if dpto else ''

        context['default_dpto'] = default_dpto
        context['current_dpto'] = current_dpto
        return context

    def get_queryset(self):
        queryset = Solicitud.objects.all()
        user = self.request.user
        user_groups = set(user.groups.values_list('name', flat=True))

        group_default_dpto = {
            'super_members': 'm',  # Mantenimiento
            'operaciones': 'o'     # Operaciones
        }

        default_dpto = ''
        for group, dpto in group_default_dpto.items():
            if group in user_groups:
                default_dpto = dpto
                break 
        
        dpto = self.request.GET.get('dpto', default_dpto)
        current_dpto = dpto if dpto else ''

        state = self.request.GET.get('state')
        asset_filter = self.request.GET.get('asset')
        keyword = self.request.GET.get('keyword')

        if asset_filter:
            queryset = queryset.filter(asset__abbreviation=asset_filter)
        if keyword:
            queryset = queryset.filter(suministros__icontains=keyword)

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

        if current_dpto:
            queryset = queryset.filter(dpto=current_dpto)

        if user.has_perm('got.can_view_all_rqs'):
            return queryset
        else:
            filter_condition = Q()

            if 'maq_members' in user_groups:
                supervised_assets = Asset.objects.filter(Q(supervisor=user) | Q(capitan=user))
                filter_condition |= Q(asset__in=supervised_assets)
            if 'serport_members' in user_groups:
                filter_condition |= Q(solicitante=user)
            if 'buzos' in user_groups:
                buceo_assets = Asset.objects.filter(area='b')
                filter_condition |= Q(asset__in=buceo_assets)

            if not filter_condition:
                filter_condition = Q(solicitante=user)
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
    

class DeleteSolicitudView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        # Verificar si el usuario es superusuario (administrador)
        return self.request.user.is_superuser

    def handle_no_permission(self):
        return HttpResponseForbidden("No tiene permiso para eliminar esta solicitud.")

    def post(self, request, *args, **kwargs):
        solicitud = get_object_or_404(Solicitud, pk=kwargs['pk'])
        solicitud.delete()
        messages.success(request, "Solicitud eliminada exitosamente.")
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


class TransferSolicitudView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'got.can_transfer_solicitud'

    def post(self, request, *args, **kwargs):
        solicitud = get_object_or_404(Solicitud, pk=kwargs['pk'])
        # Cambiar el departamento al otro valor
        if solicitud.dpto == 'o':
            solicitud.dpto = 'm'
        elif solicitud.dpto == 'm':
            solicitud.dpto = 'o'
        solicitud.save()
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


'GENERAL VIEWS'
@login_required
def indicadores(request):
    m = 1
    y = 2025

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
        ots = len(Ot.objects.filter(creation_date__month=m, creation_date__year=y, system__asset__area=area_filter))

        ot_finish = len(Ot.objects.filter(
            creation_date__month=m,
            creation_date__year=y, state='f',
            system__asset__area=area_filter))

        preventivo = len(Ot.objects.filter(
            creation_date__month=m,
            creation_date__year=y,
            tipo_mtto='p',
            system__asset__area=area_filter
            ))
        correctivo = len(Ot.objects.filter(
            creation_date__month=m,
            creation_date__year=y,
            tipo_mtto='c',
            system__asset__area=area_filter
            ))
        modificativo = len(Ot.objects.filter(
            creation_date__month=m,
            creation_date__year=y,
            tipo_mtto='m',
            system__asset__area=area_filter
            ))

    else:
        ots = len(Ot.objects.filter(
            creation_date__month=m, creation_date__year=y))
        ot_finish = len(Ot.objects.filter(
            creation_date__month=m, creation_date__year=y, state='f'))

        preventivo = len(Ot.objects.filter(
            creation_date__month=m, creation_date__year=y, tipo_mtto='p'))
        correctivo = len(Ot.objects.filter(
            creation_date__month=m, creation_date__year=y, tipo_mtto='c'))
        modificativo = len(Ot.objects.filter(
            creation_date__month=m, creation_date__year=y, tipo_mtto='m'))

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

            last_transaction = Transaction.objects.filter(suministro=suministro, tipo='c').order_by('-fecha').first()
            if last_transaction:
                last_report_date = last_transaction.fecha
            else:
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
    return render(request, 'got/assets/indicadores.html', context)


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

    return render(request, 'got/solicitud/edit_item.html', {'form': form, 'item': item})


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
                worksheet.append([asset.name, system.name, equipo.name, equipo.code])

    # Establecer el tipo de contenido de la respuesta HTTP
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=Asset_System_Equipo.xlsx'
    workbook.save(response)
    return response



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
    

class MaintenanceDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'got/mantenimiento/maintenance_dashboard.html'

    def test_func(self):
        # Verificar si el usuario pertenece al grupo 'super_members'
        return self.request.user.groups.filter(name='super_members').exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ships = Asset.objects.filter(area='a', show=True)

        # Obtener sistemas de todos los barcos y agrupar por 'group' para obtener sistemas únicos
        systems_queryset = System.objects.filter(asset__in=ships).select_related('asset')
        unique_systems = {}
        for system in systems_queryset:
            key = system.name
            if key not in unique_systems:
                unique_systems[key] = system

        # Ordenar los sistemas únicos por 'group' o como prefieras
        systems = sorted(unique_systems.values(), key=lambda s: s.name)

        # Preparar la estructura de datos
        data = []
        for ship in ships:
            ship_row = {'ship': ship.name}
            ship_systems = System.objects.filter(asset=ship).prefetch_related(
                'rutas',
                'equipos__failurereport_set',
                'ot_set',
            )

            # Crear un diccionario de sistemas del barco actual por 'group'
            ship_systems_dict = {system.name: system for system in ship_systems}

            for system in systems:
                system_group = system.name
                ship_system = ship_systems_dict.get(system_group)
                if ship_system:
                    states, state_data = self.get_system_states(ship_system)
                    ship_row[system_group] = {
                        'states': states,
                        'state_data': state_data,
                        'system_id': ship_system.id,
                    }
                else:
                    ship_row[system_group] = {'states': [], 'state_data': {}, 'system_id': None}
            data.append(ship_row)

        context['systems'] = systems
        context['data'] = data
        return context

    def get_system_states(self, system):
        states = []
        state_data = {}
        today = date.today()
        
        rutas = list(system.rutas.all())
        equipos = list(system.equipos.all())
        failure_reports = []
        
        failure_reports = FailureReport.objects.filter(
            equipo__in=equipos,
            closed=False
        ).select_related('equipo', 'related_ot').prefetch_related(
            Prefetch(
                'related_ot__task_set',
                queryset=Task.objects.filter(finished=False),
                to_attr='tasks_in_execution'
            )
        )

        ots = system.ot_set.filter(state='x').prefetch_related(
            Prefetch(
                'task_set',
                queryset=Task.objects.filter(finished=False),
                to_attr='tasks_in_execution'
            )
        )

        ots_with_tasks_in_execution = []
        ots_without_tasks_in_execution = []

        for ot in ots:
            if ot.tasks_in_execution:
                ots_with_tasks_in_execution.append(ot)
            else:
                ots_without_tasks_in_execution.append(ot)
        
        requires_maintenance = False
        all_up_to_date = True
        has_planeacion = False
        overdue_rutinas = []
        planeacion_rutinas = []

        for ruta in rutas:
            next_date = ruta.next_date
            if next_date and next_date < today:
                requires_maintenance = True
                all_up_to_date = False
                overdue_rutinas.append(ruta)
            elif not next_date:
                requires_maintenance = True
                all_up_to_date = False
                overdue_rutinas.append(ruta)
            percentage = ruta.percentage_remaining
            if percentage and 0 < percentage < 15:
                has_planeacion = True
                planeacion_rutinas.append(ruta)

        if requires_maintenance:
            states.append(('Requiere', '#ff00ff'))  # Rojo
            state_data['Requiere'] = overdue_rutinas

        if has_planeacion:
            states.append(('Planeación', '#ffff00'))  # Amarillo
            state_data['Planeación'] = planeacion_rutinas

        # Estado "Alerta"
        alerta_reports = failure_reports.filter(critico=True)
        if alerta_reports.exists():
            states.append(('Alerta', '#cc0000'))  # Rojo intenso
            state_data['Alerta'] = alerta_reports

        # Estado "Novedades"
        novedades_reports = failure_reports.filter(critico=False)
        if novedades_reports.exists():
            states.append(('Novedades', '#ffa500'))  # Naranja
            state_data['Novedades'] = novedades_reports

        # Estado "Trabajando"
        if ots_with_tasks_in_execution:
            states.append(('Trabajando', '#800080'))  # Morado
            state_data['Trabajando'] = ots_with_tasks_in_execution

        if ots_without_tasks_in_execution:
            states.append(('Pendientes', '#025669'))  # Color personalizado
            state_data['Pendientes'] = ots_without_tasks_in_execution

        if not alerta_reports.exists() and not novedades_reports.exists():
            if not requires_maintenance and all_up_to_date:
                states.append(('Ok', '#86e49d'))  # Verde

        return states, state_data


class BuceoMttoView(LoginRequiredMixin, TemplateView):
    template_name = 'got/mantenimiento/buceomtto.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        location_filter = self.request.GET.get('location', None)
        buceo_assets = Asset.objects.filter(area='b', show=True)

        all_rutinas = Ruta.objects.filter(system__asset__in=buceo_assets).exclude(system__state__in=['x', 's'])
        if location_filter:
            all_rutinas = all_rutinas.filter(system__location=location_filter)
        rutina_names = set(all_rutinas.values_list('name', flat=True))
        rutina_names = sorted(rutina_names)

        buceo_data = []
        for asset in buceo_assets:
            asset_rutinas = Ruta.objects.filter(system__asset=asset).exclude(system__state__in=['x', 's'])
            if location_filter:
                asset_rutinas = asset_rutinas.filter(system__location=location_filter)

            rutina_status = {}
            for rutina_name in rutina_names:
                rutinas = asset_rutinas.filter(name=rutina_name)
                status = self.evaluate_rutina_status(rutinas)
                rutina_status[rutina_name] = status
        
            general_states, state_data = self.evaluate_general_state(asset)

            buceo_data.append({
                'asset': asset,
                'general_states': general_states,
                'state_data': state_data,
                'rutina_status': rutina_status,
            })

        context['buceo_data'] = buceo_data
        context['rutina_names'] = rutina_names

        # Obtener las ubicaciones únicas para el filtro
        locations = System.objects.filter(asset__in=buceo_assets).values_list('location', flat=True).distinct()
        unique_locations = sorted(set(location.strip() for location in locations if location))
        context['locations'] = unique_locations
        context['current_location'] = location_filter

        return context

    def evaluate_rutina_status(self, rutinas):
        if not rutinas.exists():
            return None
        today = date.today()
        requires_maintenance = False
        all_up_to_date = True
        has_planeacion = False
        overdue_rutinas = []
        planeacion_rutinas = []

        for ruta in rutinas:
            next_date = ruta.next_date
            if next_date and next_date < today:
                requires_maintenance = True
                all_up_to_date = False
                overdue_rutinas.append(ruta)
            elif not next_date:
                requires_maintenance = True
                all_up_to_date = False
                overdue_rutinas.append(ruta)
            percentage = ruta.percentage_remaining
            if percentage and 0 < percentage < 15:
                has_planeacion = True
                planeacion_rutinas.append(ruta)

        if requires_maintenance:
            return ('Requiere', '#FF00FF', overdue_rutinas)  # Rojo
        elif has_planeacion:
            return ('Planeación', '#ffff00', planeacion_rutinas)  # Amarillo
        elif all_up_to_date:
            return ('Ok', '#86e49d', [])  # Verde
        else:
            return ('---', '#ffffff', [])  # Sin estado

    def evaluate_general_state(self, asset):
        failure_reports = FailureReport.objects.filter(
            equipo__system__asset=asset,
            equipo__system__state__in=['m', 'o'],
            closed=False
        ).select_related('equipo', 'related_ot').prefetch_related(
            Prefetch(
                'related_ot__task_set',
                queryset=Task.objects.filter(finished=False),
                to_attr='tasks_in_execution'
            )
        )

        ots = Ot.objects.filter(system__asset=asset, state='x').prefetch_related(
            Prefetch(
                'task_set',
                queryset=Task.objects.filter(finished=False),
                to_attr='tasks_in_execution'
            )
        )

        ots_with_tasks_in_execution = []
        ots_without_tasks_in_execution = []

        for ot in ots:
            if ot.tasks_in_execution:
                ots_with_tasks_in_execution.append(ot)
            else:
                ots_without_tasks_in_execution.append(ot)

        states = []
        state_data = {}

        # Estado "Alerta"
        alerta_reports = failure_reports.filter(critico=True)
        if alerta_reports.exists():
            states.append(('Alerta', '#cc0000'))  # Rojo intenso
            state_data['Alerta'] = alerta_reports

        # Estado "Novedades"
        novedades_reports = failure_reports.filter(critico=False)
        if novedades_reports.exists():
            states.append(('Novedades', '#ffa500'))  # Naranja
            state_data['Novedades'] = novedades_reports

        # Estado "Trabajando"
        if ots_with_tasks_in_execution:
            states.append(('Trabajando', '#800080'))  # Morado
            state_data['Trabajando'] = ots_with_tasks_in_execution

        # Estado "Pendientes"
        if ots_without_tasks_in_execution:
            states.append(('Pendientes', '#025669'))  # Azul oscuro
            state_data['Pendientes'] = ots_without_tasks_in_execution

        return states, state_data


class VehiculosMttoView(LoginRequiredMixin, TemplateView):
    template_name = 'got/mantenimiento/vehiculosmtto.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        veh_asset = get_object_or_404(Asset, abbreviation='VEH')

        # Obtenemos todos los sistemas asociados a este asset que estén en estado 'm' o 'o' (mantenimiento u operativo)
        systems = System.objects.filter(asset=veh_asset).exclude(state__in=['x', 's'])

        # Filtramos todas las rutinas de todos los sistemas
        all_rutinas = Ruta.objects.filter(system__in=systems)
        # Extraemos los nombres únicos de rutinas
        rutina_names = set(all_rutinas.values_list('name', flat=True))
        rutina_names = sorted(rutina_names)

        veh_data = []
        for system in systems:
            # Rutinas de este sistema
            system_rutinas = Ruta.objects.filter(system=system).exclude(system__state__in=['x', 's'])

            rutina_status = {}
            for rutina_name in rutina_names:
                rutinas = system_rutinas.filter(name=rutina_name)
                status = self.evaluate_rutina_status(rutinas)
                rutina_status[rutina_name] = status

            general_states, state_data = self.evaluate_general_state(system)

            veh_data.append({
                'system': system,  # Sistema que representa el vehiculo
                'general_states': general_states,
                'state_data': state_data,
                'rutina_status': rutina_status,
            })

        context['veh_data'] = veh_data
        context['rutina_names'] = rutina_names

        return context

    def evaluate_rutina_status(self, rutinas):
        if not rutinas.exists():
            return None
        today = date.today()
        requires_maintenance = False
        all_up_to_date = True
        has_planeacion = False
        overdue_rutinas = []
        planeacion_rutinas = []

        for ruta in rutinas:
            next_date = ruta.next_date
            if next_date and next_date < today:
                requires_maintenance = True
                all_up_to_date = False
                overdue_rutinas.append(ruta)
            elif not next_date:
                requires_maintenance = True
                all_up_to_date = False
                overdue_rutinas.append(ruta)
            percentage = ruta.percentage_remaining
            if percentage and 0 < percentage < 15:
                has_planeacion = True
                planeacion_rutinas.append(ruta)

        if requires_maintenance:
            return ('Requiere', '#cc0000', overdue_rutinas)  # Rojo
        elif has_planeacion:
            return ('Planeación', '#ffff00', planeacion_rutinas)  # Amarillo
        elif all_up_to_date:
            return ('Ok', '#86e49d', [])  # Verde
        else:
            return ('---', '#ffffff', [])  # Sin estado

    def evaluate_general_state(self, system):
        # Evaluamos el estado general del sistema: fallas y OTs
        equipos = system.equipos.all()
        failure_reports = FailureReport.objects.filter(
            equipo__in=equipos,
            closed=False
        ).select_related('equipo', 'related_ot').prefetch_related(
            Prefetch(
                'related_ot__task_set',
                queryset=Task.objects.filter(finished=False),
                to_attr='tasks_in_execution'
            )
        )

        ots = Ot.objects.filter(system=system, state='x').prefetch_related(
            Prefetch(
                'task_set',
                queryset=Task.objects.filter(finished=False),
                to_attr='tasks_in_execution'
            )
        )

        ots_with_tasks_in_execution = []
        ots_without_tasks_in_execution = []

        for ot in ots:
            if ot.tasks_in_execution:
                ots_with_tasks_in_execution.append(ot)
            else:
                ots_without_tasks_in_execution.append(ot)

        states = []
        state_data = {}

        # Estado "Alerta"
        alerta_reports = failure_reports.filter(critico=True)
        if alerta_reports.exists():
            states.append(('Alerta', '#cc0000')) 
            state_data['Alerta'] = alerta_reports

        # Estado "Novedades"
        novedades_reports = failure_reports.filter(critico=False)
        if novedades_reports.exists():
            states.append(('Novedades', '#ffa500')) 
            state_data['Novedades'] = novedades_reports

        # Estado "Trabajando"
        if ots_with_tasks_in_execution:
            states.append(('Trabajando', '#800080')) 
            state_data['Trabajando'] = ots_with_tasks_in_execution

        # Estado "Pendientes"
        if ots_without_tasks_in_execution:
            states.append(('Pendientes', '#025669'))
            state_data['Pendientes'] = ots_without_tasks_in_execution

        # Si no hay alertas ni novedades y no entra en las otras categorías, entonces está OK
        if not alerta_reports.exists() and not novedades_reports.exists():
            if not states:
                states.append(('Ok', '#86e49d'))

        return states, state_data


class ManagerialReportView(View):
    def get(self, request, *args, **kwargs):
        # Obtener todos los activos en el área de barcos ('a' corresponde a 'Motonave')
        assets = Asset.objects.filter(area='a', show=True)
        
        # Preparar datos para cada activo
        assets_data = []
        for asset in assets:
            # Información del activo
            asset_info = {
                'name': asset.name,
                'abbreviation': asset.abbreviation,
                'supervisor': asset.supervisor.get_full_name() if asset.supervisor else '',
                'maintenance_compliance': asset.maintenance_compliance,
            }

            # Obtener todos los sistemas del activo
            systems = asset.system_set.all()

            # Obtener todas las rutas de los sistemas
            rutas = Ruta.objects.filter(system__in=systems)

            # Filtrar rutas vencidas o próximas a vencer
            rutas_filtered = []
            for ruta in rutas:
                percentage_remaining = ruta.percentage_remaining
                if percentage_remaining < 15:
                    # Determinar tiempo restante
                    if ruta.control == 'd':
                        tiempo_restante = ruta.daysleft
                        unidad = 'días'
                    elif ruta.control == 'h' or ruta.control == 'k':
                        accumulated_hours = ruta.equipo.hours.filter(
                            report_date__gte=ruta.intervention_date,
                            report_date__lte=date.today()
                        ).aggregate(total_hours=Sum('hour'))['total_hours'] or 0
                        tiempo_restante = ruta.frecuency - accumulated_hours
                        unidad = 'horas'
                    else:
                        tiempo_restante = ''
                        unidad = ''

                    # Recopilar la información requerida
                    ruta_info = {
                        'equipo': ruta.equipo.name if ruta.equipo else '',
                        'name': ruta.name,
                        'frecuencia': ruta.frecuency,
                        'tiempo_restante': tiempo_restante,
                        'unidad': unidad,
                        'fecha_ultima_intervencion': ruta.intervention_date,
                        'fecha_proxima_intervencion': ruta.next_date,
                        'overdue': percentage_remaining <= 0,
                    }
                    rutas_filtered.append(ruta_info)
            equipos = Equipo.objects.filter(system__in=systems)
            failure_reports = FailureReport.objects.filter(
                equipo__in=equipos,
                closed=False
            )

            failure_reports_data = []
            for report in failure_reports:
                report_data = {
                    'id': report.id,
                    'description': report.description,
                    'equipo': report.equipo.name if report.equipo else '',
                    'ot': None,
                    'tasks': [],
                }

                if report.related_ot:
                    ot = report.related_ot
                    ot_info = {
                        'num_ot': ot.num_ot,
                        'description': ot.description,
                        'state': ot.get_state_display(),
                    }
                    report_data['ot'] = ot_info

                    # Obtener actividades en ejecución relacionadas con la OT
                    tasks_in_execution = Task.objects.filter(ot=ot, finished=False)
                    tasks_data = []
                    for task in tasks_in_execution:
                        task_info = {
                            'description': task.description,
                            'start_date': task.start_date,
                            'responsible': task.responsible.get_full_name() if task.responsible else '',
                        }
                        tasks_data.append(task_info)
                    report_data['tasks'] = tasks_data

                failure_reports_data.append(report_data)

            asset_info['rutas'] = rutas_filtered
            asset_info['failure_reports'] = failure_reports_data

            assets_data.append(asset_info)

        context = {
            'assets': assets_data,
            'today': date.today(),
        }

        return render_to_pdf('got/managerial_report.html', context)

    
class BudgetView(TemplateView):
    template_name = 'got/mantenimiento/budget_view.html'

    def get_assets_list(self):
        return Asset.objects.filter(area='a', show=True).order_by('name')

    def get_systems_list(self, asset_abbr):
        return System.objects.filter(asset__abbreviation=asset_abbr).order_by('name')

    def get_equipos_list(self, system_id):
        return Equipo.objects.filter(system_id=system_id).order_by('name')

    def get(self, request, *args, **kwargs):
        asset_abbr = request.GET.get('asset_abbr', '')
        system_id = request.GET.get('system_id', '')
        equipo_code = request.GET.get('equipo_code', '')

        period_start = date(2025, 1, 1)
        period_end = date(2025, 12, 31)

        # Obtener rutas según filtros
        rutas = Ruta.objects.all()
        if asset_abbr:
            rutas = rutas.filter(system__asset__abbreviation=asset_abbr)
        if system_id:
            rutas = rutas.filter(system_id=system_id)
        if equipo_code:
            rutas = rutas.filter(equipo__code=equipo_code)

        item_totals = {}
        service_totals = {}

        systems_with_reqs = set()

        # Cálculo de num_executions y totales
        for ruta in rutas:
            num_executions = calculate_executions(ruta, period_start, period_end)
            if num_executions == 0:
                continue

            requisitos = ruta.requisitos.all()
            if requisitos.exists():
                # Si esta ruta tiene requisitos, entonces este system_id tiene requerimientos
                systems_with_reqs.add(ruta.system_id)

            for req in requisitos:
                total_quantity = req.cantidad * num_executions
                if req.tipo in ['m', 'h']:
                    if req.item:
                        key = req.item.id
                        name = req.item
                        presentacion = req.item.presentacion
                        unit_price = req.item.unit_price if getattr(req.item, 'unit_price', None) else Decimal('0.00')
                        reference = req.item.reference if req.item.reference else ''
                    else:
                        key = ('desc', req.descripcion)
                        name = req.descripcion
                        presentacion = 'Sin presentación'
                        unit_price = Decimal('0.00')
                        reference = ''

                    if key not in item_totals:
                        item_totals[key] = {
                            'name': name,
                            'presentacion': presentacion,
                            'total_quantity': total_quantity,
                            'num_executions': num_executions,
                            'unit_price': unit_price,
                            'reference': reference,
                            'type': 'item',
                            'id': key if isinstance(key, int) else None
                        }
                    else:
                        item_totals[key]['total_quantity'] += total_quantity
                        item_totals[key]['num_executions'] += num_executions

                elif req.tipo == 's':
                    if req.service:
                        key = req.service.id
                        name = req.service.description
                        presentacion = 'Serv'
                        unit_price = req.service.unit_price if req.service.unit_price else Decimal('0.00')
                        reference = ''
                    else:
                        key = ('desc_s', req.descripcion)
                        name = req.descripcion
                        presentacion = 'Serv'
                        unit_price = Decimal('0.00')
                        reference = ''

                    if key not in service_totals:
                        service_totals[key] = {
                            'name': name,
                            'presentacion': presentacion,
                            'total_quantity': total_quantity,
                            'num_executions': num_executions,
                            'unit_price': unit_price,
                            'type': 'service',
                            'id': key if isinstance(key, int) else None
                        }
                    else:
                        service_totals[key]['total_quantity'] += total_quantity
                        service_totals[key]['num_executions'] += num_executions

        # Calcular costos
        for item in item_totals.values():
            item['total_cost'] = item['total_quantity'] * item['unit_price']

        for svc in service_totals.values():
            svc['total_cost'] = svc['total_quantity'] * svc['unit_price']

        # Ordenar
        item_list = list(item_totals.values())
        item_list.sort(key=lambda x: (
            str(x['name'].name).lower() if hasattr(x['name'], 'name') and x['name'].name else str(x['name']).lower(),
            x['reference'].lower() if x['reference'] else ''
        ))
        service_list = list(service_totals.values())
        service_list.sort(key=lambda x: str(x['name'] or '').lower())

        total_articulos = sum(i['total_cost'] for i in item_list)
        total_servicios = sum(s['total_cost'] for s in service_list)

        # Calcular micelanios (10%)
        micelanios_articulos = total_articulos * Decimal('0.10')
        micelanios_servicios = total_servicios * Decimal('0.10')

        # Nuevos totales incluyendo micelanios
        total_articulos_with_micelanios = total_articulos + micelanios_articulos
        total_servicios_with_micelanios = total_servicios + micelanios_servicios

        # Calcular total combinado
        combined_total = total_articulos_with_micelanios + total_servicios_with_micelanios

        # Obtener listas para filtros
        assets = self.get_assets_list()
        systems = self.get_systems_list(asset_abbr) if asset_abbr else []
        equipos = self.get_equipos_list(system_id) if system_id else []

        enabled_systems = set()
        if asset_abbr:
            for sys in systems:
                if sys.id in systems_with_reqs:
                    enabled_systems.add(sys.id)

        context = {
            'item_totals': item_list,
            'service_totals': service_list,
            'period_start': period_start,
            'period_end': period_end,
            'total_articulos': total_articulos,
            'micelanios_articulos': micelanios_articulos,
            'total_articulos_with_micelanios': total_articulos_with_micelanios,
            'total_servicios': total_servicios,
            'micelanios_servicios': micelanios_servicios,
            'total_servicios_with_micelanios': total_servicios_with_micelanios,
            'combined_total': combined_total,
            'assets_list': assets,
            'selected_asset': asset_abbr,
            'systems_list': systems,
            'selected_system': system_id,
            'equipos_list': equipos,
            'selected_equipo': equipo_code,
            'enabled_systems': enabled_systems
        }

        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        if action == 'update_unit_price':
            obj_type = request.POST.get('obj_type')
            obj_id = request.POST.get('obj_id')
            new_price = request.POST.get('new_price')
            try:
                new_price = Decimal(new_price)
            except:
                new_price = Decimal('0.00')

            if obj_type == 'item':
                item = get_object_or_404(Item, pk=obj_id)
                item.unit_price = new_price
                item.save()
                messages.success(request, 'Precio del artículo actualizado.')
            elif obj_type == 'service':
                svc = get_object_or_404(Service, pk=obj_id)
                svc.unit_price = new_price
                svc.save()
                messages.success(request, 'Precio del servicio actualizado.')
            else:
                messages.error(request, 'Tipo no reconocido.')

            # Mantener filtros
            asset_abbr = request.GET.get('asset_abbr', '')
            system_id = request.GET.get('system_id', '')
            equipo_code = request.GET.get('equipo_code', '')

            redirect_url = reverse('got:budget_view')
            query_params = []
            if asset_abbr:
                query_params.append(f"asset_abbr={asset_abbr}")
            if system_id:
                query_params.append(f"system_id={system_id}")
            if equipo_code:
                query_params.append(f"equipo_code={equipo_code}")
            if query_params:
                redirect_url += "?" + "&".join(query_params)

            return redirect(redirect_url)
        else:
            messages.error(request, 'Acción no reconocida.')
            return redirect('got:budget_view')

from django.db.models import Q

class BudgetSummaryByAssetView(TemplateView):
    template_name = 'got/mantenimiento/budget_summary_view.html'

    def get(self, request, *args, **kwargs):
        period_start = date(2025, 1, 1)
        period_end   = date(2025, 12, 31)

        # 1. Definir las condiciones usando Q
        condition_barcos = Q(area='a', show=True)
        condition_otros   = Q(show=True) & ~Q(area='a') & Q(system__rutas__requisitos__isnull=False)

        # 2. Filtrar los assets que cumplen alguna de las condiciones
        all_assets = Asset.objects.filter(
            condition_barcos | condition_otros
        ).distinct().order_by('name')

        assets_data = []
        total_global = Decimal('0.00')
        micelanios_global = Decimal('0.00')

        for barco in all_assets:
            rutas = Ruta.objects.filter(system__asset=barco)
            costo_total_barco = Decimal('0.00')
            equipos_dict = {}
            categories_dict = {
                'Aceite y Filtros': Decimal('0.00'),
                'Servicios':        Decimal('0.00'),
                'Repuestos':        Decimal('0.00')
            }

            for ruta in rutas:
                num_exec = calculate_executions(ruta, period_start, period_end)
                if num_exec == 0:
                    continue

                equipo_id = ruta.equipo_id or 'otros'

                for req in ruta.requisitos.all():
                    unit_price = Decimal('0.00')
                    if req.tipo in ['m', 'h'] and req.item:
                        unit_price = req.item.unit_price or Decimal('0.00')
                    elif req.tipo == 's' and req.service:
                        unit_price = req.service.unit_price or Decimal('0.00')

                    subtotal = req.cantidad * unit_price * num_exec
                    equipos_dict.setdefault(equipo_id, Decimal('0.00'))
                    equipos_dict[equipo_id] += subtotal

                    # Clasificar en categories_dict
                    if req.tipo in ['m', 'h'] and req.item:
                        if req.item.name in ["Aceite", "Filtros"]:
                            categories_dict['Aceite y Filtros'] += subtotal
                        else:
                            categories_dict['Repuestos'] += subtotal
                    elif req.tipo == 's' and req.service:
                        categories_dict['Servicios'] += subtotal

            # 3. Calcular costos + micelanios
            for value in equipos_dict.values():
                costo_total_barco += value

            micelanios_barco = costo_total_barco * Decimal('0.10')
            costo_total_barco_with_micelanios = costo_total_barco + micelanios_barco

            total_global += costo_total_barco_with_micelanios
            micelanios_global += micelanios_barco

            # 4. Convertir dict equipos a lista
            equipos_list = []
            for eq_id, cost_eq in equipos_dict.items():
                if eq_id == 'otros':
                    eq_name = 'Otros'
                else:
                    try:
                        eq_obj = Equipo.objects.get(pk=eq_id)
                        eq_name = eq_obj.name
                    except Equipo.DoesNotExist:
                        eq_name = 'Desconocido'
                equipos_list.append({
                    'equipo_name': eq_name,
                    'cost': float(cost_eq)
                })
            equipos_list.sort(key=lambda e: e['equipo_name'].lower())

            # Datos para gráficas
            labels_equipos = [eq['equipo_name'] for eq in equipos_list]
            data_equipos = [eq['cost'] for eq in equipos_list]

            labels_categories = ['Aceite y Filtros', 'Servicios', 'Repuestos']
            data_categories = [
                float(categories_dict['Aceite y Filtros']),
                float(categories_dict['Servicios']),
                float(categories_dict['Repuestos'])
            ]

            assets_data.append({
                'asset_id':        barco.abbreviation,
                'asset_name':      barco.name,
                'asset_cost':      float(costo_total_barco_with_micelanios),
                'micelanios':      float(micelanios_barco),
                'equipos':         equipos_list,
                'labels_equipos':  labels_equipos,
                'data_equipos':    data_equipos,
                'types_labels':    labels_categories,
                'types_data':      data_categories,
            })

        # 5. Preparar datos para la gráfica principal
        pie_labels = []
        pie_data   = []
        for asset_info in assets_data:
            pie_labels.append(asset_info['asset_name'])
            pie_data.append(asset_info['asset_cost'])

        # Opcional: agregar "Micelanios" global
        pie_labels.append("Micelanios")
        pie_data.append(float(micelanios_global))

        # Convertir a JSON
        assets_data_json = json.dumps(assets_data)
        pie_labels_json  = json.dumps(pie_labels)
        pie_data_json    = json.dumps(pie_data)

        context = {
            'period_start':       period_start,
            'period_end':         period_end,
            'total_global':       float(total_global),
            'micelanios_global':  float(micelanios_global),
            'assets_data':        assets_data,
            'assets_data_json':   assets_data_json,
            'pie_labels':         pie_labels_json,
            'pie_data':           pie_data_json,
        }
        return self.render_to_response(context)


def managerial_asset_report_pdf(request, abbreviation):
    asset = get_object_or_404(Asset, abbreviation=abbreviation)
    systems = asset.system_set.all()

    systems_data = []
    for sys in systems:
        # Equipos y sus imágenes
        equipos_qs = sys.equipos.all()
        equipos_data = []
        for eq in equipos_qs:
            # Filtramos imágenes asociadas al equipo
            eq_images = eq.images.all().order_by('id')
            # Omitir los campos None => lo haremos en la plantilla

            equipos_data.append({
                'name': eq.name,
                'ubicacion': eq.ubicacion,
                'code': eq.code,
                'model': eq.model,
                'marca': eq.marca,
                'serial': eq.serial,
                'fabricante': eq.fabricante,
                'tipo_display': eq.get_tipo_display(),
                'feature': eq.feature,
                'all_images': eq_images,
            })

        # OTs en ejecución
        ots_en_x = sys.ot_set.filter(state='x')
        ots_en_ejecucion_data = []
        for ot in ots_en_x:
            open_tasks = ot.task_set.filter(finished=False)
            ots_en_ejecucion_data.append({
                'num_ot': ot.num_ot,
                'description': ot.description,
                'open_tasks': open_tasks,
            })

        # Fallas abiertas sin OT
        # => Recolectamos todos los equipos IDs
        eq_ids = equipos_qs.values_list('pk', flat=True)
        failures_abiertas = FailureReport.objects.filter(
            equipo_id__in=eq_ids,
            closed=False,
            related_ot__isnull=True
        )

        systems_data.append({
            'system': sys,
            'equipments': equipos_data,
            'ots_en_ejecucion': ots_en_ejecucion_data,
            'failures_abiertas': failures_abiertas,
        })

    context = {
        'asset': asset,
        'systems_data': systems_data,
        'today': timezone.now().date(),
    }

    return render_to_pdf('got/systems/managerial_asset_report.html', context)
