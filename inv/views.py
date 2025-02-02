# inventory_management/views.py
import base64
import qrcode
from io import BytesIO
import re
import qrcode.image.svg
from itertools import groupby
from operator import attrgetter

from django.contrib.auth.decorators import permission_required, login_required
from django.core.files.base import ContentFile
from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.http import HttpResponseRedirect
from got.models import Asset, System, Equipo, Suministro, Item
from got.forms import ItemForm
from got.utils import *
from .models import DarBaja
from .forms import *
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView
from got.utils import get_full_systems_ids
from django.views.decorators.csrf import csrf_exempt
import openpyxl
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter
import io
from django.http import HttpResponse
from openpyxl import Workbook
from django.shortcuts import redirect
from django.contrib import messages
from django.db.models import Count, Q, OuterRef, Subquery, F, ExpressionWrapper, DateField, Prefetch, Sum, Max, Case, When, IntegerField, BooleanField, Value
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.template.loader import render_to_string



class ActivoEquipmentListView(View):
    template_name = 'inventory_management/asset_equipment_list.html'

    def get(self, request, abbreviation):
        activo = get_object_or_404(Asset, abbreviation=abbreviation)
        sistemas_ids = get_full_systems_ids(activo, request.user)
        # Optimizar la consulta de equipos
        equipos = Equipo.objects.filter(system__in=sistemas_ids).select_related('system').prefetch_related('images')

        # Optimizar la consulta de suministros
        suministros = Suministro.objects.filter(asset=activo).select_related('item')

        # Optimizar la consulta de items (si es necesario)
        all_items = Item.objects.all().only('id', 'name', 'reference', 'seccion', 'presentacion').order_by('name')

        suministros = Suministro.objects.filter(asset=activo).select_related('item')
        all_items = Item.objects.all().only('id', 'name', 'reference', 'seccion', 'presentacion').order_by('name')

        context = {
            'activo': activo,
            'equipos': equipos,
            'fecha_actual': timezone.now().date(),
            'suministros': suministros,
            'all_items': all_items,
        }
        return render(request, self.template_name, context)


class EquipoDetailPartialView(View):
    def get(self, request, eq_id):
        equipo = get_object_or_404(Equipo, pk=eq_id)
        context = {
            'equipo': equipo,
        }
        html = render_to_string('inventory_management/partial_equipo_detail.html', context, request=request)
        return HttpResponse(html)
    

@csrf_exempt
def public_equipo_detail(request, eq_code):
    """
    Vista pública (sin login) con la info completa de un equipo.
    Sin barra de navegación ni estilos de la app "base".
    """
    equipo = get_object_or_404(Equipo, code=eq_code)
    system = equipo.system  # model: System
    asset = system.asset    # model: Asset

    images = equipo.images.all().order_by('id')

    context = {
        'equipo': equipo,
        'system': system,
        'asset': asset,
        'images': images,
        # 'rutas': rutas, 'daily_fuel': daily_fuel, etc.
    }
    return render(request, 'inventory_management/public_equipo_detail.html', context)


def export_equipment_supplies(request, abbreviation):
    """
    Genera un archivo Excel con dos secciones:
    1) Lista de Equipos del Activo
    2) Lista de Suministros del Activo
    usando la función pro_export_to_excel (adaptándola para 2 sheets).
    """
    # 1. Obtener el Activo
    asset = get_object_or_404(Asset, abbreviation=abbreviation)

    # 2. Recolectar datos de Equipos
    #    Filtra todos los equipos de los sistemas de este activo
    systems = asset.system_set.all()
    equipos_qs = Equipo.objects.filter(system__in=systems).order_by('name')

    # Cabeceras (columnas) para "Equipos"
    equipment_headers = [
        'Código', 'Nombre', 'Tipo', 'Modelo', 'Marca', 'Serial',
        'Fabricante', 'Ubicación', 'Sistema', 'Activo',
        'Horómetro/Km', 'Promedio horas/día', 'Volumen', 'Recomendaciones'
        # Agrega las columnas que desees
    ]

    # Construimos las filas
    equipment_data = []
    for eq in equipos_qs:
        system_name = eq.system.name
        asset_name = eq.system.asset.name
        # Para Horómetro/kilometraje
        if eq.system.asset.area == 'v':
            # Vehículo => interpretamos eq.horometro como km
            horo_value = f"{eq.horometro} km"
        else:
            horo_value = f"{eq.horometro} h"

        row = [
            eq.code,
            eq.name,
            eq.get_tipo_display(),
            eq.model or "",
            eq.marca or "",
            eq.serial or "",
            eq.fabricante or "",
            eq.ubicacion or system_name,  # default eq.system.location, ajusta según gustes
            system_name,
            asset_name,
            horo_value,
            str(eq.prom_hours or 0),
            str(eq.volumen or ""),
            (eq.recomendaciones or "").replace('\n', ' '),
        ]
        equipment_data.append(row)

    # 3. Recolectar datos de Suministros
    suministros_qs = Suministro.objects.filter(asset=asset).select_related('item')
    # Cabeceras para "Suministros"
    supply_headers = [
        'Artículo', 'Referencia', 'Presentación', 'Cantidad'
        # añade más si tu Suministro/item tiene más info
    ]

    supply_data = []
    for s in suministros_qs:
        if s.item:
            supply_data.append([
                s.item.name,
                s.item.reference or "",
                s.item.presentacion or "",
                str(s.cantidad)
            ])
        else:
            # Suministro sin item
            supply_data.append([
                "(Sin artículo)",
                "",
                "",
                str(s.cantidad)
            ])

    wb = Workbook()
    ws_equips = wb.active
    ws_equips.title = "Equipos"

    # Título en la hoja
    current_row = 1
    # Encabezados
    for col_num, header in enumerate(equipment_headers, 1):
        cell = ws_equips.cell(row=current_row, column=col_num)
        cell.value = header
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center', vertical='center')

    # Datos
    for row_data in equipment_data:
        current_row += 1
        for col_num, cell_value in enumerate(row_data, 1):
            cell = ws_equips.cell(row=current_row, column=col_num)
            cell.value = cell_value

    # Ajuste de anchos
    for idx, column_cells in enumerate(ws_equips.columns, 1):
        length = max(len(str(cell.value)) if cell.value else 0 for cell in column_cells)
        col_letter = get_column_letter(idx)
        ws_equips.column_dimensions[col_letter].width = length + 2

    # 2DA HOJA => Suministros
    ws_supp = wb.create_sheet(title="Suministros")

    # Encabezados
    current_row = 1
    for col_num, header in enumerate(supply_headers, 1):
        cell = ws_supp.cell(row=current_row, column=col_num)
        cell.value = header
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center', vertical='center')

    # Datos
    for row_data in supply_data:
        current_row += 1
        for col_num, cell_value in enumerate(row_data, 1):
            cell = ws_supp.cell(row=current_row, column=col_num)
            cell.value = cell_value

    for idx, column_cells in enumerate(ws_supp.columns, 1):
        length = max(len(str(cell.value)) if cell.value else 0 for cell in column_cells)
        col_letter = get_column_letter(idx)
        ws_supp.column_dimensions[col_letter].width = length + 2

    # 5. Exportar a HttpResponse
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"{asset.abbreviation}_Equipos_y_Suministros.xlsx"
    response = HttpResponse(
        output,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename={filename}'
    return response


class AllAssetsEquipmentListView(View):
    """
    Muestra una vista muy similar a ActivoEquipmentListView,
    pero incluyendo TODOS los activos (show=True),
    y en la tabla de equipos y suministros se incluye una columna adicional con el Activo.
    """
    template_name = 'inventory_management/all_equipment_list.html'

    def get(self, request):
        # 1) Lista de TODOS los Activos (show=True), sin excluir nada:
        all_activos = (
            Asset.objects.filter(show=True)
            .select_related('supervisor', 'capitan')
            .order_by('name')
        )

        # 2) Obtener todos los sistemas de esos activos
        all_systems = System.objects.filter(asset__in=all_activos)

        # 3) Todos los equipos de esos sistemas
        equipos = Equipo.objects.filter(system__in=all_systems).order_by('name')

        # 4) Todos los suministros asociados a esos activos
        suministros = Suministro.objects.filter(asset__in=all_activos).select_related('item')

        # 5) Generar un QR para cada equipo (opcional, si lo deseas)
        domain = "https://got.serport.co"
        for eq in equipos:
            # Por ejemplo, generamos un link público:
            public_url = f"{domain}/inv/public/equipo/{eq.code}/"
            qr = qrcode.QRCode(version=1, box_size=4, border=2)
            qr.add_data(public_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            qr_io = BytesIO()
            img.save(qr_io, format='PNG')
            eq.qr_code_b64 = base64.b64encode(qr_io.getvalue()).decode('utf-8')

        # 6) Si deseas, obtén también la lista de Item para "crear nuevo suministro"
        all_items = Item.objects.all().order_by('name')

        context = {
            'all_activos': all_activos,  # Para scroll horizontal, si quieres
            'equipos': equipos,
            'suministros': suministros,
            'all_items': all_items,
            # Fecha actual, etc.
            'fecha_actual': timezone.now().date(),
        }
        return render(request, self.template_name, context)


class DarBajaCreateView(LoginRequiredMixin, CreateView):
    model = DarBaja
    form_class = DarBajaForm
    template_name = 'inventory_management/dar_baja_form.html'

    def get_equipo(self):
        equipo_code = self.kwargs['equipo_code']
        return get_object_or_404(Equipo, code=equipo_code)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        equipo = self.get_equipo()
        context['equipo'] = equipo

        # Instanciar el segundo formulario (evidencias + firmas)
        if self.request.method == 'POST':
            context['upload_form'] = UploadEvidenciasYFirmasForm(self.request.POST, self.request.FILES)
        else:
            context['upload_form'] = UploadEvidenciasYFirmasForm()
        return context

    def form_valid(self, form):
        # 1) Guardar DarBaja => self.object
        equipo = self.get_equipo()
        user = self.request.user
        form.instance.equipo = equipo
        form.instance.reporter = user.get_full_name() or user.username
        form.instance.activo = f"{equipo.system.asset.name} - {equipo.system.name}"

        # Guardamos de forma normal
        response = super().form_valid(form)  # => crea self.object

        # 2) Procesar upload_form
        upload_form = self.get_context_data()['upload_form']
        if not upload_form.is_valid():
            messages.error(self.request, "Error en el formulario de subida de archivos.")
            self.object.delete()
            return self.form_invalid(form)

        # Tomar subidas de firma
        fr_file = upload_form.cleaned_data.get('firma_responsable_file')
        fa_file = upload_form.cleaned_data.get('firma_autorizado_file')

        # Tomar data base64 de canvas
        firma_responsable_data = self.request.POST.get('firma_responsable_data', '')
        firma_autorizado_data = self.request.POST.get('firma_autorizado_data', '')

        # Chequeo => O suben archivo o dibujan la firma
        if not fr_file and not firma_responsable_data:
            messages.error(self.request, "Debe proporcionar la firma Responsable (archivo o dibujo).")
            self.object.delete()
            return self.form_invalid(form)

        if not fa_file and not firma_autorizado_data:
            messages.error(self.request, "Debe proporcionar la firma Autorizado (archivo o dibujo).")
            self.object.delete()
            return self.form_invalid(form)

        # Firma Responsable
        if fr_file:
            if not fr_file.content_type.startswith('image/'):
                messages.error(self.request, "Archivo de firma responsable no es válido.")
                self.object.delete()
                return self.form_invalid(form)
            self.object.firma_responsable = fr_file
            self.object.save(update_fields=['firma_responsable'])
        else:
            # Canvas base64
            fmt, imgstr = firma_responsable_data.split(';base64,')
            ext = fmt.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr))
            self.object.firma_responsable.save(f'firma_responsable_{self.object.pk}.{ext}', data, save=True)

        # Firma Autorizado
        if fa_file:
            if not fa_file.content_type.startswith('image/'):
                messages.error(self.request, "Archivo de firma autorizado no es válido.")
                self.object.delete()
                return self.form_invalid(form)
            self.object.firma_autorizado = fa_file
            self.object.save(update_fields=['firma_autorizado'])
        else:
            fmt, imgstr = firma_autorizado_data.split(';base64,')
            ext = fmt.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr))
            self.object.firma_autorizado.save(f'firma_autorizado_{self.object.pk}.{ext}', data, save=True)

        # 3) Evidencias => multiple
        evidences = upload_form.cleaned_data['file_field']  # lista de archivos
        for file_obj in evidences:
            if not file_obj.content_type.startswith('image/'):
                messages.error(self.request, "Uno de los archivos de evidencia no es una imagen válida.")
                self.object.delete()
                return self.form_invalid(form)
            Image.objects.create(image=file_obj, darbaja=self.object)

        # 4) Eliminar rutinas/hours/etc
        self.do_equipo_cleanup(equipo)

        # 5) Mover equipo a system 445
        new_system = System.objects.get(id=445)
        old_system = equipo.system
        equipo.system = new_system
        equipo.save()
        messages.success(self.request, f'El equipo ha sido trasladado al sistema {new_system.name}.')

        # 6) Generar PDF (opcional)
        self.generate_pdf()

        # 7) Redirigir => 'activos/<str:abbreviation>/equipos/'
        return redirect(self.get_success_url())

    def do_equipo_cleanup(self, equipo):
        # Eliminar rutinas, hours, etc.
        ...
        # (Idéntico a tu lógica actual)

    def generate_pdf(self):
        context = {
            'dar_baja': self.object,
            'equipo': self.object.equipo
        }
        pdf = render_to_pdf('inventory_management/dar_baja_pdf.html', context)
        if pdf:
            # Podrías guardarlo en disco, o en la base de datos, 
            # o ignorarlo si solo deseas generarlo internamente
            filename = f'dar_baja_{self.object.pk}.pdf'
            # Ejemplo: guardarlo en un directorio local (opcional)
            # with open(f'/tmp/{filename}', 'wb') as f:
            #     f.write(pdf.getvalue())
        else:
            messages.warning(self.request, 'No se pudo generar el PDF.')

    def get_success_url(self):
        # Redirigir a: path('activos/<str:abbreviation>/equipos/', name='asset_equipment_list'),
        # old_system.asset.abbreviation => => 'inv:asset_equipment_list'
        abbreviation = self.object.equipo.system.asset.abbreviation
        return reverse('inv:asset_equipment_list', kwargs={'abbreviation': abbreviation})


def create_supply_view(request, abbreviation):
    """
    Crea un nuevo Suministro asociado a un Activo.
    Opcionalmente crea un nuevo Item si el usuario marcó "is_new_item == 1".
    """
    asset = get_object_or_404(Asset, abbreviation=abbreviation)

    if request.method == 'POST':
        is_new_item = request.POST.get('is_new_item', '0')
        cantidad_str = request.POST.get('cantidad')

        # Validar cantidad
        if not cantidad_str:
            messages.error(request, "Debe especificar la cantidad.")
            return redirect('inv:asset_equipment_list', abbreviation=abbreviation)

        try:
            cantidad = float(cantidad_str)
        except ValueError:
            messages.error(request, "Cantidad inválida.")
            return redirect('inv:asset_equipment_list', abbreviation=abbreviation)

        # Caso A: Crear artículo nuevo
        if is_new_item == '1':
            form_data = {
                'name': request.POST.get('new_item_name'),
                'reference': request.POST.get('new_item_reference'),
                'presentacion': request.POST.get('new_item_presentacion'),
                'code': request.POST.get('new_item_code'),
                'seccion': request.POST.get('new_item_seccion'),
                'unit_price': request.POST.get('new_item_unit_price') or 0.00,
            }
            files_data = {}
            if 'new_item_imagen' in request.FILES:
                files_data['imagen'] = request.FILES['new_item_imagen']

            item_form = ItemForm(form_data, files_data)
            if item_form.is_valid():
                new_item = item_form.save(commit=False)
                if request.user.is_authenticated:
                    new_item.modified_by = request.user
                new_item.save()
                item = new_item
                messages.success(request, f"Artículo '{item.name}' creado correctamente.")
            else:
                messages.error(request, f"Error al crear el artículo: {item_form.errors}")
                return redirect('inv:asset_equipment_list', abbreviation=abbreviation)

        # Caso B: Se usa un artículo existente
        else:
            item_id = request.POST.get('item_id')
            if not item_id:
                messages.error(request, "Debe seleccionar un artículo existente o crear uno nuevo.")
                return redirect('inv:asset_equipment_list', abbreviation=abbreviation)

            try:
                item = Item.objects.get(id=item_id)
            except Item.DoesNotExist:
                messages.error(request, "El artículo seleccionado no existe.")
                return redirect('inv:asset_equipment_list', abbreviation=abbreviation)

        # Crear el Suministro
        Suministro.objects.create(
            item=item,
            cantidad=cantidad,
            asset=asset
        )
        messages.success(request, f"Se ha creado un nuevo suministro de '{item.name}' para {asset.name}.")
        return redirect('inv:asset_equipment_list', abbreviation=abbreviation)

    # Si no es POST => redirigir sin hacer nada
    return redirect('inv:asset_equipment_list', abbreviation=abbreviation)


class AssetInventoryBaseView(LoginRequiredMixin, View):
    template_name = 'got/assets/asset_inventory_report.html'
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

        elif action == 'transfer_suministro':
            suministro_id = request.POST.get('transfer_suministro_id')
            suministro = get_object_or_404(Suministro, id=suministro_id, asset=asset)
            transfer_fecha_str = request.POST.get('transfer_fecha', '')

            if not re.match(r'^\d{4}-\d{2}-\d{2}$', transfer_fecha_str):
                messages.error(request, "Fecha inválida de transferencia: usa el formato YYYY-MM-DD.")
                return self.redirect_with_next(request)
            
            try:
                transfer_fecha = datetime.strptime(transfer_fecha_str, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, "Fecha inválida: no se pudo interpretar el valor ingresado.")
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

            print(fecha_reporte_str)
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

        elif action == 'add_suministro' and request.user.has_perm('got.can_add_supply'):
            item_id = request.POST.get('item_id')
            item = get_object_or_404(Item, id=item_id)
            suministro_existente = Suministro.objects.filter(asset=asset, item=item).exists()
            if suministro_existente:
                messages.error(request, f'El suministro para el artículo "{item.name}" ya existe en este asset.')
            else:
                Suministro.objects.create(item=item, cantidad=Decimal('0.00'), asset=asset)
                messages.success(request, f'Suministro para "{item.name}" creado exitosamente.')
            return self.redirect_with_next(request)

        else:
            messages.error(request, 'Acción no reconocida.')
            return self.redirect_with_next(request)

    def get_context_data(self, request, asset, suministros, transacciones_historial, ultima_fecha_transaccion):
        motonaves = Asset.objects.filter(show=True)
        available_items = Item.objects.exclude(id__in=suministros.values_list('item_id', flat=True))
        users_en_historial = transacciones_historial.values_list('user', flat=True).distinct()
        users_unicos = User.objects.filter(username__in=users_en_historial).order_by('username')
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
        next_url = request.GET.get('next', '')
        if next_url:
            return redirect(next_url)
        return redirect(request.path)


class AssetSuministrosReportView(AssetInventoryBaseView):
    keyword_filter = Q(item__name__icontains='Combustible') | Q(item__name__icontains='Aceite') | Q(item__name__icontains='Filtro')

    keyword_filter2 = (
        Q(suministro__item__name__icontains='Combustible')
        | Q(suministro__item__name__icontains='Aceite')
        | Q(suministro__item__name__icontains='Filtro')
    )

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
        secciones_dict = dict(Item.SECCION)
        context['secciones_dict'] = secciones_dict

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
            # Cantidad inicial: latest 'cant_report' before 'fecha_inicio'
            if fecha_inicio:
                trans_before_start = Transaction.objects.filter(
                    suministro=suministro,
                    fecha__lte=fecha_inicio
                ).order_by('-fecha').first()
                cantidad_inicial = trans_before_start.cant_report if trans_before_start and trans_before_start.cant_report else Decimal('0.00')
            else:
                cantidad_inicial = Decimal('0.00')

            # Total consumido: sum of 'c' transactions in the period
            total_consumido = transacciones.filter(
                suministro=suministro,
                tipo='c'
            ).aggregate(total=Sum('cant'))['total'] or Decimal('0.00')

            # Total ingresado: sum of 'i' transactions in the period
            total_ingresado = transacciones.filter(
                suministro=suministro,
                tipo='i'
            ).aggregate(total=Sum('cant'))['total'] or Decimal('0.00')

            # Cantidad final: latest 'cant_report' before 'fecha_fin'
            if fecha_fin:
                trans_before_end = Transaction.objects.filter(
                    suministro=suministro,
                    fecha__lte=fecha_fin
                ).order_by('-fecha').first()
                cantidad_final = trans_before_end.cant_report if trans_before_end and trans_before_end.cant_report else Decimal('0.00')
            else:
                # Si no hay fecha_fin, usar la última cantidad reportada hasta hoy
                trans_before_end = Transaction.objects.filter(
                    suministro=suministro,
                    fecha__lte=date.today()
                ).order_by('-fecha').first()
                cantidad_final = trans_before_end.cant_report if trans_before_end and trans_before_end.cant_report else Decimal('0.00')

            suministros_summary.append({
                'suministro': suministro,
                'cantidad_inicial': cantidad_inicial,
                'total_consumido': total_consumido,
                'total_ingresado': total_ingresado,
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


@login_required
def transferir_equipo(request, equipo_id):
    equipo = get_object_or_404(Equipo, pk=equipo_id)
    if request.method == 'POST':
        # form = TransferenciaForm(request.POST)
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
    return render(request, 'inventory_management/transferencias.html', context)