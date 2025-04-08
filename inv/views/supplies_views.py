# inv/views/supplies_views.py
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from decimal import Decimal, InvalidOperation

from got.models.asset import Asset
from got.models.others import Item
from got.forms import ItemForm
from inv.models import Suministro


@login_required
@permission_required('inv.can_add_supply', raise_exception=True)
def create_new_item_supply_view(request, abbreviation):
    """
    Crea un nuevo Suministro (asset+item+cantidad). 
    Si 'is_new_item'=1, crea un nuevo Item. 
    Caso contrario, se usa un Item existente.
    Valida:
      - Cantidad > 0
      - No exista ya un Suministro con (asset, item)
    Responde con messages.* y redirect a 'inv:asset_equipment_list' (sin JSON).
    """
    asset = get_object_or_404(Asset, abbreviation=abbreviation)

    if request.method != 'POST':
        # No es POST => simplemente redirigir sin hacer nada.
        return redirect('inv:asset_equipment_list', abbreviation=abbreviation)

    # 1) Extraer campos
    is_new_item = request.POST.get('is_new_item', '0')
    cantidad_str = (request.POST.get('cantidad', '')).strip()

    # 2) Validar cantidad > 0
    if not cantidad_str:
        messages.error(request, "Debe especificar la cantidad.")
        return redirect('inv:asset_equipment_list', abbreviation=abbreviation)
    try:
        cantidad_dec = Decimal(cantidad_str)
    except (InvalidOperation, ValueError):
        messages.error(request, "Cantidad inválida (no es un número).")
        return redirect('inv:asset_equipment_list', abbreviation=abbreviation)

    if cantidad_dec <= 0:
        messages.error(request, "La cantidad debe ser mayor que cero.")
        return redirect('inv:asset_equipment_list', abbreviation=abbreviation)

    # 3) Crear item nuevo O usar uno existente
    if is_new_item == '1':
        # Crear artículo nuevo a partir de los campos “new_item_*”
        form_data = {
            'name': request.POST.get('new_item_name', '').strip(),
            'reference': request.POST.get('new_item_reference', '').strip(),
            'presentacion': request.POST.get('new_item_presentacion', '').strip(),
            'code': request.POST.get('new_item_code', '').strip(),
            'seccion': request.POST.get('new_item_seccion', 'c'),
            'unit_price': request.POST.get('new_item_unit_price', '0.00'),
        }
        files_data = {}
        if 'new_item_imagen' in request.FILES:
            files_data['imagen'] = request.FILES['new_item_imagen']

        item_form = ItemForm(form_data, files_data)
        if not item_form.is_valid():
            messages.error(request, f"Error al crear el artículo: {item_form.errors}")
            return redirect('inv:asset_equipment_list', abbreviation=abbreviation)

        # Guardar el nuevo Item
        item = item_form.save(commit=False)
        if request.user.is_authenticated:
            item.modified_by = request.user
        item.save()

        messages.success(request, f"Artículo '{item.name}' creado correctamente.")
    else:
        # Caso usar un Item existente
        item_id = request.POST.get('item_id')
        if not item_id:
            messages.error(request, "Debe seleccionar un artículo existente o crear uno nuevo.")
            return redirect('inv:asset_equipment_list', abbreviation=abbreviation)
        try:
            item = Item.objects.get(pk=item_id)
        except Item.DoesNotExist:
            messages.error(request, "El artículo seleccionado no existe.")
            return redirect('inv:asset_equipment_list', abbreviation=abbreviation)

    # 4) Evitar duplicados en Suministro
    if Suministro.objects.filter(asset=asset, item=item).exists():
        messages.error(request, f"El suministro para '{item.name}' ya existe en {asset.name}.")
        return redirect('inv:asset_equipment_list', abbreviation=abbreviation)

    # 5) Crear Suministro
    Suministro.objects.create(item=item, cantidad=cantidad_dec, asset=asset)
    messages.success(request, f"Suministro '{item.name}' (cant={cantidad_dec}) creado en {asset.name}.")
    return redirect('inv:asset_equipment_list', abbreviation=abbreviation)
