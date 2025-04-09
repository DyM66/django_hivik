from got.models import Equipo, Asset
from inv.models.inventory import Suministro, Transaction
from inv.models.equipment_retirement import RetiredSupply, RetiredSupplyImage

from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django import db
from django.db import models
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404


def get_suministros(asset, keyword_filter):
    """
    Obtiene los suministros filtrados por un filtro de palabras clave.

    :param asset: Instancia de Asset.
    :param keyword_filter: Filtro Q para filtrar los artículos.
    :return: QuerySet de suministros filtrados.
    """
    suministros = Suministro.objects.filter(asset=asset).filter(keyword_filter).select_related('item').order_by('item__seccion')
    return suministros

def supplies_summary(asset):
    equipos = Equipo.objects.filter(system__asset=asset).prefetch_related('suministros__item')
    item_subsystems = defaultdict(set)
    items_by_subsystem = defaultdict(set)
    item_cant = defaultdict(set)

    inventory_counts = defaultdict(int)
    suministros = Suministro.objects.filter(asset=asset)

    for suministro in suministros:
        inventory_counts[suministro.item] += suministro.cantidad

    for equipo in equipos:
        subsystem = equipo.subsystem if equipo.subsystem else "General"
        for suministro in equipo.suministros.all():
                item_subsystems[suministro.item].add(subsystem)
                if suministro.item in item_cant:
                    item_cant[suministro.item] += suministro.cantidad
                else:
                    item_cant[suministro.item] = suministro.cantidad
    
    duplicated_items = {item for item, subsystems in item_subsystems.items() if len(subsystems) > 1}

    for equipo in equipos:
        subsystem = equipo.subsystem if equipo.subsystem else "General"
        for suministro in equipo.suministros.all():
            item_tuple = (suministro.item, item_cant[suministro.item], inventory_counts[suministro.item], item_cant[suministro.item] * 2)
            if suministro.item in duplicated_items:
                items_by_subsystem["General"].add(item_tuple)
            else:
                items_by_subsystem[subsystem].add(item_tuple)
    
    items_by_subsystem = {k: list(v) for k, v in items_by_subsystem.items() if v}

    return items_by_subsystem


def recalc_suministro_from_date(suministro, from_date):
    """
    Recalcula transacciones 'i', 'c' y 't' que afecten a este suministro
    desde 'from_date' en adelante, incluyendo caso origen (suministro) y destino (suministro_transf).

    Pasos:
      1) Buscar la última transacción (i, c, t) con fecha < from_date (sea origen o destino)
         para obtener el acumulado "hasta ese día".
      2) Tomar TODAS las transacciones (i,c,t) con fecha >= from_date donde
         (suministro = este suministro) OR (suministro_transf = este suministro)
         para procesarlas en orden ascendente por fecha, id.
      3) Sumar/restar la cantidad según sea 'i', 'c' o 't'(origen/destino).
      4) Guardar en t.cant_report o t.cant_report_transf, según corresponda.
      5) Actualizar suministro.cantidad al final.
      6) Si el acumulado cae < 0 en cualquier punto, lanzar ValueError.
    """

    from decimal import Decimal
    
    # 1) Hallar la última transacción (cualquier tipo) ANTES de from_date
    #    donde este suministro sea origen O destino
    base_trans = Transaction.objects.filter(
        (
            models.Q(suministro=suministro) | models.Q(suministro_transf=suministro)
        ),
        tipo__in=['i','c','t'],
        fecha__lt=from_date
    ).order_by('-fecha','-id').first()

    # Hallar el acumulado base
    if base_trans:
        if base_trans.tipo in ('i','c'):
            # Se usa base_trans.cant_report
            acumulado = base_trans.cant_report or Decimal('0.00')
        else:  # es 't'
            if base_trans.suministro_id == suministro.id:
                # Origen
                acumulado = base_trans.cant_report or Decimal('0.00')
            elif base_trans.suministro_transf_id == suministro.id:
                # Destino
                acumulado = base_trans.cant_report_transf or Decimal('0.00')
            else:
                # No debería pasar, pero por seguridad
                acumulado = Decimal('0.00')
    else:
        acumulado = Decimal('0.00')

    # 2) Transacciones >= from_date donde este suministro sea origen O destino
    trans_posteriores = Transaction.objects.filter(
        (
            models.Q(suministro=suministro) | models.Q(suministro_transf=suministro)
        ),
        tipo__in=['i','c','t'],
        fecha__gte=from_date
    ).order_by('fecha','id')

    # 3) Recorrer y sumar/restar
    for t in trans_posteriores:
        if t.tipo == 'i':
            # Este suministro es t.suministro
            # sumamos
            acumulado += t.cant
            t.cant_report = acumulado
            t.cant_report_transf = None  # no aplica
        elif t.tipo == 'c':
            # restamos
            acumulado -= t.cant
            if acumulado < 0:
                raise ValueError(
                    f"Inventario negativo en transacción id={t.id}, fecha={t.fecha}, acumulado={acumulado}"
                )
            t.cant_report = acumulado
            t.cant_report_transf = None
        elif t.tipo == 't':
            # Transferencia => verificar si somos ORIGEN o DESTINO
            if t.suministro_id == suministro.id:
                # ORIGEN => acumulado -= t.cant
                acumulado -= t.cant
                if acumulado < 0:
                    raise ValueError(
                        f"Inventario negativo en transacción id={t.id} (origen), fecha={t.fecha}, acumulado={acumulado}"
                    )
                # Guardamos en cant_report (campo del origen)
                t.cant_report = acumulado
                # Dejamos cant_report_transf intacto
            elif t.suministro_transf_id == suministro.id:
                # DESTINO => acumulado += t.cant
                acumulado += t.cant
                if acumulado < 0:
                    raise ValueError(
                        f"Inventario negativo en transacción id={t.id} (destino), fecha={t.fecha}, acumulado={acumulado}"
                    )
                # Guardamos en cant_report_transf
                t.cant_report_transf = acumulado
            else:
                # no debería suceder
                pass
        t.save()

    # 4) Actualizar la cantidad final del suministro
    suministro.cantidad = acumulado
    suministro.save()


def handle_inventory_update(request, asset, suministros, motivo_global=''):
    """
    Actualiza las transacciones de cada suministro (ingresos/consumos) para la fecha dada en el formulario.

    Reglas principales:
      - Fecha de reporte NO puede ser > hoy.
      - Cualquier usuario puede CREAR transacciones en fechas <= hoy.
      - Para SOBRESCRIBIR (editar) transacciones existentes:
         * Si el usuario tiene 'inv.change_transaction', no hay restricción (hasta hoy).
         * Si NO tiene 'inv.change_transaction' pero SÍ 'inv.can_edit_only_today', 
           solo puede editar transacciones con fecha >= (hoy - 5 días).
      - Ignoramos cualquier valor de ingreso o consumo que sea <= 0 o no-numérico.
      - Si, tras ignorar valores inválidos, no queda NINGÚN cambio válido, se avisa y se aborta.
      - Si hay transacciones existentes de tipo 'i' o 'c' en esa fecha, se pide confirmación "confirm_overwrite".
      - Recalcula inventario parcial. Rollback si cae en negativo.
    """

    fecha_reporte_str = request.POST.get('fecha_reporte', timezone.now().date().strftime('%Y-%m-%d'))
    confirm_overwrite = request.POST.get('confirm_overwrite', 'no')

    observaciones_adicionales = request.POST.get('observaciones_global', '').strip()

    motivo_concat = motivo_global
    if observaciones_adicionales:
        motivo_concat = f"{motivo_global} - {observaciones_adicionales}"

    # 1) Parsear la fecha
    try:
        fecha_reporte = datetime.strptime(fecha_reporte_str, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, 'Fecha inválida. Use el formato YYYY-MM-DD.')
        return redirect(request.path)

    hoy = timezone.now().date()
    if fecha_reporte > hoy:
        messages.error(request, 'No se permiten reportes en fechas futuras.')
        return redirect(request.path)

    # Lista para acumulación de sobrescrituras
    overwriting_transactions = []
    # Bandera para saber si AL MENOS un suministro tiene valores de ingreso/consumo válidos (> 0)
    at_least_one_valid = False

    # 2) Primera pasada: verificar cuáles transacciones se van a sobrescribir, 
    #    y validar permisos en caso de edición
    for suministro in suministros:
        consumido_str = request.POST.get(f'consumido_{suministro.id}', '0') or '0'
        ingresado_str = request.POST.get(f'ingresado_{suministro.id}', '0') or '0'

        # Parsear
        try:
            cant_cons = Decimal(consumido_str)
            cant_ingr = Decimal(ingresado_str)
        except InvalidOperation:
            # Si no es un número, lo ignoramos (se considera 0)
            cant_cons = Decimal('0')
            cant_ingr = Decimal('0')

        # Ignorar si ambos <= 0 => no hay cambio real
        # (No generamos error: el requerimiento dice "ignorar si no es un número positivo")
        if cant_cons <= 0 and cant_ingr <= 0:
            continue

        # Ya sabemos que al menos uno > 0 => marcado como "válido"
        at_least_one_valid = True

        # Si existen transacciones en esa fecha => SOBRESCRIBIR => validar
        existing_ingreso = Transaction.objects.filter(
            suministro=suministro, fecha=fecha_reporte, tipo='i'
        ).first() if cant_ingr > 0 else None
        existing_consumo = Transaction.objects.filter(
            suministro=suministro, fecha=fecha_reporte, tipo='c'
        ).first() if cant_cons > 0 else None

        # Validación de edición solo si la transacción YA existe
        if existing_ingreso or existing_consumo:
            # Si NO tiene 'inv.change_transaction', 
            #   => chequear la fecha sea >= hoy - 5
            if not request.user.has_perm('inv.change_transaction'):
                cinco_dias_atras = hoy - timedelta(days=5)
                if fecha_reporte < cinco_dias_atras:
                    messages.error(
                        request,
                        ("No está autorizado para editar transacciones con más de 5 días de antigüedad. "
                         f"Suministro: {suministro.item.name}, fecha: {fecha_reporte}.")
                    )
                    return redirect(request.path)

            # Si no se confirma la sobrescritura
            if confirm_overwrite != 'yes':
                if existing_ingreso:
                    overwriting_transactions.append(('Ingreso', existing_ingreso))
                if existing_consumo:
                    overwriting_transactions.append(('Consumo', existing_consumo))

    # Si tras iterar NO se encontraron transacciones válidas => error
    if not at_least_one_valid:
        messages.error(request, 'No se proporcionó ningún valor positivo de ingreso o consumo. Operación cancelada.')
        return redirect(request.path)

    # Si hay sobrescrituras y no se han confirmado => pedir confirmación
    if overwriting_transactions:
        context = {
            'asset': asset,
            'overwriting_transactions': overwriting_transactions,
            'post_data': request.POST,
        }
        return render(request, 'got/assets/confirm_overwrite.html', context)

    earliest_modified_date = None
    modified_suministros = set()

    with db.transaction.atomic():
        for suministro in suministros:
            consumido_str = request.POST.get(f'consumido_{suministro.id}', '0') or '0'
            ingresado_str = request.POST.get(f'ingresado_{suministro.id}', '0') or '0'
            skip_remision = request.POST.get(f'skip_remision_{suministro.id}', 'no')
            try:
                cant_cons = Decimal(consumido_str)
                cant_ingr = Decimal(ingresado_str)
            except InvalidOperation:
                cant_cons = Decimal('0')
                cant_ingr = Decimal('0')

            # Ignorar si ambos <= 0 => sin cambios
            if cant_cons <= 0 and cant_ingr <= 0:
                continue

            # INGRESO
            if cant_ingr > 0:
                file_key = f"remision_{suministro.id}"
                remision_file = request.FILES.get(file_key, None)
                justificacion = request.POST.get(f"justificacion_{suministro.id}", "")

                concat_motivo = motivo_global
                if justificacion.strip():
                    concat_motivo += f" - [INGRESO EXTERNO: {justificacion}]"

                trans_ing, created = Transaction.objects.get_or_create(
                    suministro=suministro,
                    fecha=fecha_reporte,
                    tipo='i',
                    defaults={
                        'cant': cant_ingr,
                        'user': request.user.get_full_name(),
                        'motivo': motivo_concat,
                        'cant_report': Decimal('0'),
                    }
                )
                if not created:
                    # Sobrescribir
                    trans_ing.cant = cant_ingr
                    trans_ing.user = request.user.get_full_name()
                    trans_ing.motivo = motivo_global or request.POST.get('motivo', '')
                
                if remision_file:
                    trans_ing.remision = remision_file

                trans_ing.motivo = concat_motivo
                trans_ing.save()

            # CONSUMO
            if cant_cons > 0:
                trans_con, created = Transaction.objects.get_or_create(
                    suministro=suministro,
                    fecha=fecha_reporte,
                    tipo='c',
                    defaults={
                        'cant': cant_cons,
                        'user': request.user.get_full_name(),
                        'motivo': motivo_global or request.POST.get('motivo', ''),
                        'cant_report': Decimal('0'),
                    }
                )
                if not created:
                    trans_con.cant = cant_cons
                    trans_con.user = request.user.get_full_name()
                    trans_con.motivo = motivo_global or request.POST.get('motivo', '')
                    trans_con.save()

            # Ajustar earliest_modified_date
            if earliest_modified_date is None or fecha_reporte < earliest_modified_date:
                earliest_modified_date = fecha_reporte
            modified_suministros.add(suministro.id)

        # 4) Recalcular
        if earliest_modified_date:
            # Ajusta la ruta del import según tu proyecto
            from inv.utils.supplies_utils import recalc_suministro_from_date  
            for suministro_id in modified_suministros:
                sumi = Suministro.objects.select_for_update().get(pk=suministro_id)
                try:
                    recalc_suministro_from_date(sumi, earliest_modified_date)
                except ValueError as e:
                    messages.error(request, f"Error: {e}. Se ha revertido la operación.")
                    return redirect(request.path)

    messages.success(request, 'Inventario actualizado exitosamente.')
    return redirect(request.path)

def handle_transfer(request, asset, suministro, transfer_cantidad_str, destination_asset_id, transfer_motivo, transfer_fecha_str):
    """
    Maneja la transferencia de un suministro de 'asset' (origen) a 'destination_asset_id' (destino),
    creando/sobrescribiendo una transacción de tipo 't', y recalculando el inventario en ambos.
    
    Validaciones:
      - No puede ser fecha futura.
      - Si sobrescribe (existe 't' en esa fecha y suministro), 
        y el user no tiene 'inv.change_transaction', la fecha debe ser >= hoy - 5.
      - Cantidad debe ser > 0.
      - Confirmar sobrescritura con 'confirm_overwrite' si ya existía.
      - Se recalc_suministro_from_date(suministro, transfer_fecha) y recalc_suministro_from_date(destino, transfer_fecha),
        que ahora incluye 't'.
      - Al final, se dejan trans_t.cant_report y trans_t.cant_report_transf con los valores finales.
    """
    confirm_overwrite = request.POST.get('confirm_overwrite', 'no')

    try:
        transfer_fecha = datetime.strptime(transfer_fecha_str, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, 'Fecha inválida. Use formato YYYY-MM-DD.')
        return redirect(request.path)

    hoy = timezone.now().date()
    if transfer_fecha > hoy:
        messages.error(request, 'No se permiten transferencias en fechas futuras.')
        return redirect(request.path)

    # Parsear la cantidad
    try:
        transfer_cantidad = Decimal(transfer_cantidad_str)
    except InvalidOperation:
        transfer_cantidad = Decimal('0')

    if transfer_cantidad <= 0:
        messages.error(request, 'No se proporcionó una cantidad positiva para la transferencia. Operación cancelada.')
        return redirect(request.path)

    # Detectar sobrescritura
    existing_transaction = Transaction.objects.filter(
        suministro=suministro,
        fecha=transfer_fecha,
        tipo='t'
    ).first()

    # Si existe => validar edición
    if existing_transaction:
        if not request.user.has_perm('inv.change_transaction'):
            cinco_dias_atras = hoy - timedelta(days=5)
            if transfer_fecha < cinco_dias_atras:
                messages.error(
                    request,
                    f"No está autorizado para editar transferencias con más de 5 días de antigüedad (fecha={transfer_fecha})."
                )
                return redirect(request.path)

        if confirm_overwrite != 'yes':
            context = {
                'asset': asset,
                'overwriting_transactions': [('Transferencia', existing_transaction)],
                'post_data': request.POST,
            }
            return render(request, 'got/assets/confirm_overwrite.html', context)

    # Comenzamos la transacción atómica
    from django.db import transaction
    destination_asset = get_object_or_404(Asset, abbreviation=destination_asset_id)

    with transaction.atomic():
        suministro_destino, _ = Suministro.objects.get_or_create(
            asset=destination_asset,
            item=suministro.item,
            defaults={'cantidad': Decimal('0.00')}
        )

        # Revertir si hay existing_transaction
        if existing_transaction:
            old_cant = existing_transaction.cant
            # Sumar de vuelta al origen
            suministro.cantidad += old_cant
            # Restar al destino
            if existing_transaction.suministro_transf_id == suministro_destino.id:
                suministro_destino.cantidad -= old_cant

        # Revisar disponibilidad antes de restar
        if transfer_cantidad > suministro.cantidad:
            messages.error(request, 'La cantidad a transferir excede la disponible. Operación cancelada.')
            return redirect(request.path)

        # Aplicar la nueva transferencia
        suministro.cantidad -= transfer_cantidad
        suministro_destino.cantidad += transfer_cantidad

        suministro.save()
        suministro_destino.save()

        # Crear / sobrescribir transacción 't'
        if existing_transaction:
            existing_transaction.cant = transfer_cantidad
            existing_transaction.user = request.user.get_full_name()
            existing_transaction.motivo = transfer_motivo
            existing_transaction.suministro_transf = suministro_destino
            existing_transaction.cant_report = Decimal('0.00')       # Se actualizará tras recalc
            existing_transaction.cant_report_transf = Decimal('0.00')
            existing_transaction.save()
            trans_t = existing_transaction
        else:
            trans_t = Transaction.objects.create(
                suministro=suministro,
                cant=transfer_cantidad,
                fecha=transfer_fecha,
                user=request.user.get_full_name(),
                motivo=transfer_motivo,
                tipo='t',
                suministro_transf=suministro_destino,
                cant_report=Decimal('0.00'),
                cant_report_transf=Decimal('0.00'),
            )

        # 1) Recalcular para el suministro origen
        try:
            recalc_suministro_from_date(suministro, transfer_fecha)
        except ValueError as e:
            messages.error(request, f"Error en la transferencia (origen): {e}. Se ha revertido la operación.")
            return redirect(request.path)

        # 2) Recalcular para el suministro destino
        try:
            recalc_suministro_from_date(suministro_destino, transfer_fecha)
        except ValueError as e:
            messages.error(request, f"Error en la transferencia (destino): {e}. Se ha revertido la operación.")
            return redirect(request.path)

        # 3) Al terminar el recálculo, la transacción 't' ya debe tener
        #    cant_report (si este suministro es el origen) y cant_report_transf (si el destino) actualizados
        #    PERO para asegurarnos, refrescamos la transacción desde DB y guardamos
        trans_t.refresh_from_db()
        # Si deseas FORZAR manualmente los valores según .cantidad en cada suministro, podrías hacer:
        # trans_t.cant_report = suministro.cantidad
        # trans_t.cant_report_transf = suministro_destino.cantidad
        # trans_t.save()

    messages.success(
        request,
        (f"Transferencia de {transfer_cantidad} {suministro.item.name} realizada a {destination_asset.name} "
         f"en fecha {transfer_fecha}.")
    )
    return None  # o return redirect(...) si prefieres


def handle_delete_transaction(request, transaccion):
    with db.transaction.atomic():
        suministro_origen = transaccion.suministro
        suministro_destino = transaccion.suministro_transf

        # Revertir las cantidades según el tipo de transacción
        if transaccion.tipo == 'i':
            # Al eliminar un INGRESO, revertimos la entrada en el suministro de origen
            nueva_cantidad = suministro_origen.cantidad - transaccion.cant
            if nueva_cantidad < 0:
                messages.error(
                    request,
                    (f"No se puede eliminar la transacción de ingreso (ID={transaccion.id}) "
                     f"porque dejaría el inventario negativo en el suministro {suministro_origen.item}.")
                )
                return  # rollback implícito
            # Si no es negativo, aplicamos el cambio
            suministro_origen.cantidad = nueva_cantidad
            suministro_origen.save()
        elif transaccion.tipo == 'c':
            suministro_origen.cantidad += transaccion.cant

        elif transaccion.tipo == 't':
            # Al eliminar una TRANSFERENCIA, devolvemos la cantidad al origen y la quitamos al destino
            nueva_cantidad_origen = suministro_origen.cantidad + transaccion.cant
            nueva_cantidad_destino = suministro_destino.cantidad - transaccion.cant

            # Checamos que ninguno quede negativo
            if nueva_cantidad_origen < 0:
                messages.error(
                    request,
                    (f"No se puede eliminar la transferencia (ID={transaccion.id}), "
                     f"pues dejaría inventario negativo en el origen {suministro_origen.item}.")
                )
                return
            if nueva_cantidad_destino < 0:
                messages.error(
                    request,
                    (f"No se puede eliminar la transferencia (ID={transaccion.id}), "
                     f"pues dejaría inventario negativo en el destino {suministro_destino.item}.")
                )
                return

            suministro_origen.cantidad = nueva_cantidad_origen
            suministro_destino.cantidad = nueva_cantidad_destino

            suministro_origen.save()
            suministro_destino.save()
        elif transaccion.tipo == 'r':
            retired_supply = transaccion.retired_supply
            if retired_supply:
                # 2.1) Revertir cantidad
                suminst = transaccion.suministro
                suminst.cantidad += transaccion.cant
                suminst.save(update_fields=['cantidad'])

                # 2.2) Eliminar imágenes
                retired_supply.images.all().delete()  # si definiste related_name='images' en RetiredSupplyImage

                # 2.3) Eliminar el registro de RetiredSupply
                retired_supply.delete()
        else:
            # Otros tipos si existen, manejarlos de forma similar o abortar
            messages.error(request, "Transacción de tipo desconocido, no se pudo eliminar.")
            return

        # Si llegamos aquí, significa que no quedamos con cantidades negativas.
        # Eliminamos la transacción definitivamente.
        transaccion.delete()

    # Fuera del atomic, confirmamos
    messages.success(request, 'La transacción ha sido eliminada y las cantidades han sido actualizadas.')
    # Puedes retornar None o un redirect, según tu flujo.
    return