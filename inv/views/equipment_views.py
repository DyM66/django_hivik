from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import CreateView, UpdateView
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction, IntegrityError
from django.contrib import messages
from django.urls import reverse
from django.forms import modelformset_factory
from django.utils.http import urlencode
from django.views import View
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from got.models import Asset, System, Equipo, Image, Item
from got.forms import UploadImages, ItemForm
from got.utils import generate_equipo_code, get_full_systems_ids
from inv.forms import EquipoForm

from inv.models import Suministro

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


class EquipoCreateView(LoginRequiredMixin, CreateView):
    model = Equipo
    form_class = EquipoForm
    template_name = 'got/systems/equipo_form.html'
    http_method_names = ['get', 'post']

    def dispatch(self, request, *args, **kwargs):
        self.next_url = request.GET.get('next') or request.POST.get('next') or ''
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['system'] = get_object_or_404(System, pk=self.kwargs['pk']) # Se inyecta el objeto system en los argumentos del formulario
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Se instancia el formulario de carga de imágenes
        context['upload_form'] = UploadImages(self.request.POST, self.request.FILES) if self.request.method == 'POST' else UploadImages()
        context['sys'] = get_object_or_404(System, pk=self.kwargs['pk'])
        return context

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        upload_form = UploadImages(request.POST, request.FILES)
        if form.is_valid() and upload_form.is_valid():
            return self.form_valid(form, upload_form)
        else:
            return self.form_invalid(form, upload_form)

    def form_valid(self, form, upload_form):
        system = get_object_or_404(System, pk=self.kwargs['pk'])
        form.instance.system = system
        asset_abbreviation = system.asset.abbreviation
        tipo = form.cleaned_data['tipo'].upper()

        try:
            with transaction.atomic():
                form.instance.code = generate_equipo_code(asset_abbreviation, tipo)
                form.instance.modified_by = self.request.user
                response = super().form_valid(form)
        except IntegrityError:
            form.add_error('code', 'Error al generar un código único. Por favor, inténtalo de nuevo.')
            return self.form_invalid(form, upload_form)

        for file in self.request.FILES.getlist('file_field'):
            Image.objects.create(image=file, equipo=self.object)
        messages.success(self.request, "Equipo creado exitosamente.")
        return response

    def form_invalid(self, form, upload_form):
        context = self.get_context_data(form=form, upload_form=upload_form)
        return self.render_to_response(context)

    def get_success_url(self):
        "Redirige a la URL 'next' si está presente; de lo contrario redirige a la vista de detalle del sistema."
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
        try:
            obj = self.get_object()
        except Equipo.DoesNotExist:
            messages.error(request, "El equipo que intentas actualizar ya no existe. Por favor, actualiza la URL.")
            return redirect('got:asset-list')
        
        if str(obj.pk) != kwargs.get('pk'):
            return redirect(obj.get_absolute_url())
        
        self.object = obj
        self.next_url = request.GET.get('next') or request.POST.get('next') or ''
        self.next_to = request.GET.get('next_to') or request.POST.get('next') or ''
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        equipo = self.get_object()
        kwargs['system'] = get_object_or_404(System, equipos=equipo)
        return kwargs
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        self.old_tipo = obj.tipo  
        self.old_code = obj.code
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Formulario para carga de imágenes
        context['upload_form'] = UploadImages(self.request.POST, self.request.FILES) if self.request.method == 'POST' else UploadImages()
        ImageFormset = modelformset_factory(Image, fields=('image',), extra=0)
        context['image_formset'] = ImageFormset(queryset=self.object.images.all())
        context['image_count'] = self.object.images.count()
        context['next_url'] = self.next_url
        context['next_to'] = self.next_to
        return context
    
    def form_valid(self, form):
        form.instance.modified_by = self.request.user
        response = super().form_valid(form)
        new_tipo = self.object.tipo  # el "tipo" que el usuario seleccionó 
        new_code = self.object.code 

        # if new_tipo != self.old_tipo:
        #     # Llamar a la función update_equipo_code con el code viejo
        #     update_equipo_code(self.old_code)
        #     messages.info(
        #         self.request, 
        #         f"El tipo cambió de '{self.old_tipo}' a '{new_tipo}'. Se actualizó el código del equipo."
        #     )
        
        upload_form = self.get_context_data()['upload_form']
        if upload_form.is_valid():
            for file in self.request.FILES.getlist('file_field'):
                Image.objects.create(image=file, equipo=self.object)
                print(file)
        return response
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if "delete_image" in request.POST: # Opción para eliminar imagen vía formulario tradicional (fallback)
            image_id = request.POST.get("delete_image")
            Image.objects.filter(id=image_id, equipo=self.object).delete()
            return redirect(self.get_success_url())
        return super().post(request, *args, **kwargs)
    
    def get_success_url(self):
        url = reverse('got:equipo-detail', kwargs={'pk': self.object.pk})
        if self.next_to:
            params = {'previous_url': self.next_to}
            url = f"{url}?{urlencode(params)}"
        elif self.next_url:
            return self.next_url
        return url


class ActivoEquipmentListView(View):
    template_name = 'inventory_management/asset_equipment_list.html'

    def get(self, request, abbreviation):
        activo = get_object_or_404(Asset, abbreviation=abbreviation)
        sistemas_ids = get_full_systems_ids(activo, request.user)
        equipos = Equipo.objects.filter(system__in=sistemas_ids).select_related('system').prefetch_related('images')
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
    

class AllAssetsEquipmentListView(View):
    template_name = 'inventory_management/all_equipment_list.html'

    def get(self, request):
        all_activos = Asset.objects.filter(show=True).select_related('supervisor', 'capitan').order_by('name')
        all_systems = System.objects.filter(asset__in=all_activos)
        equipos = Equipo.objects.filter(system__in=all_systems).order_by('name')
        suministros = Suministro.objects.filter(asset__in=all_activos).select_related('item')
        all_items = Item.objects.all().order_by('name')

        context = {
            'all_activos': all_activos,
            'equipos': equipos,
            'suministros': suministros,
            'all_items': all_items,
            'fecha_actual': timezone.now().date(),
        }
        return render(request, self.template_name, context)



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
