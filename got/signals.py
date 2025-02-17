from django.db.models.signals import post_save, post_delete, pre_delete, pre_save
from django.dispatch import receiver
from django.db.models import Avg, Sum, Min
from decimal import Decimal
from datetime import datetime
from dth.models import UserProfile
from inv.models import Transaction
from .models import *


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    instance.profile.save()

@receiver(pre_save, sender=Solicitud)
def update_solicitud_dates(sender, instance, **kwargs):
    if instance.id is not None:
        old_instance = Solicitud.objects.get(id=instance.id)
        
        if not old_instance.approved and instance.approved:
            instance.approval_date = timezone.now()

        if not old_instance.num_sc and instance.num_sc:
            instance.sc_change_date = timezone.now()

        if not old_instance.num_sc and instance.cancel:
            instance.cancel_date = timezone.now()

@receiver(post_save, sender=HistoryHour)
@receiver(post_delete, sender=HistoryHour)
def update_equipo_horometro(sender, instance, **kwargs):
    equipo = instance.component
    ultimos_10_registros = HistoryHour.objects.filter(component=equipo).order_by('-report_date')[:15]
    promedio_horas = ultimos_10_registros.aggregate(promedio_horas=Avg('hour'))['promedio_horas']
    equipo.prom_hours = promedio_horas or 0
    equipo.horometro = equipo.calculate_horometro()
    equipo.save()
    update_fuel_consumption_for_asset(equipo, instance.report_date)

def update_fuel_consumption_for_asset(equipo, fecha):
    asset = equipo.system.asset
    equipos = Equipo.objects.filter(system__asset=asset, tipo='r')

    fecha_primer_reporte = Transaction.objects.filter(
        suministro__asset=asset, suministro__item__id=132,  # ID del combustible
        tipo='c').aggregate(primer_fecha=Min('fecha'))['primer_fecha']    

    # Obtener las horas totales del asset en la fecha dada
    total_horas_asset = HistoryHour.objects.filter(component__system__asset=asset, report_date=fecha).aggregate(Sum('hour'))['hour__sum'] or 0

    suministro_combustible = Transaction.objects.filter(suministro__asset=asset, suministro__item__id=132, fecha=fecha, tipo='c').aggregate(total_consumed=Sum('cant'))['total_consumed'] or 0

    if suministro_combustible > 0 and total_horas_asset > 0:
        consumo_historico_total = DailyFuelConsumption.objects.filter(
            equipo__system__asset=asset,
            fecha__gte=fecha_primer_reporte  # Filtrar desde la fecha del primer reporte
        ).aggregate(Sum('com_estimado_motor'))['com_estimado_motor__sum'] or 0

        # Actualizar el consumo estimado para cada equipo
        for equipo in equipos:
            horas_hoy = HistoryHour.objects.filter(component=equipo, report_date=fecha).aggregate(Sum('hour'))['hour__sum'] or 0

            if horas_hoy > 0:
                horas_hoy = Decimal(horas_hoy)
                total_horas_asset = Decimal(total_horas_asset)
                consumo_historico_motor = DailyFuelConsumption.objects.filter(
                    equipo=equipo,
                    fecha__gte=fecha_primer_reporte
                ).aggregate(Sum('com_estimado_motor'))['com_estimado_motor__sum'] or 0

                if consumo_historico_total > 0 and len(equipos) > 1:
                    factor_correccion = consumo_historico_motor / consumo_historico_total
                else:
                    factor_correccion = Decimal(1) 

                consumo_estimado = (horas_hoy / total_horas_asset) * suministro_combustible * factor_correccion

                # Actualizar o crear el registro de DailyFuelConsumption
                DailyFuelConsumption.objects.update_or_create(equipo=equipo, fecha=fecha, defaults={'com_estimado_motor': consumo_estimado})

@receiver(post_save, sender=Transaction)
def create_daily_fuel_consumption(sender, instance, **kwargs):
    suministro = instance.suministro

    if suministro.item.id == 132 and instance.tipo == 'c':  # ID del combustible
        asset = suministro.asset

        fecha_primer_reporte = Transaction.objects.filter(
            suministro__asset=asset, suministro__item__id=132,  # ID del combustible
            tipo='c').aggregate(primer_fecha=Min('fecha'))['primer_fecha']  

        if isinstance(instance.fecha, str):
            today = datetime.strptime(instance.fecha, '%Y-%m-%d').date()
        else:
            today = instance.fecha
        
        equipos = Equipo.objects.filter(system__asset=asset, tipo='r')

        for equipo in equipos:
            horas_hoy = HistoryHour.objects.filter(component=equipo, report_date=today).aggregate(Sum('hour'))['hour__sum'] or 0
            if horas_hoy == 0:
                continue
            
            total_horas_asset = HistoryHour.objects.filter(component__system__asset=equipo.system.asset, report_date=today).aggregate(Sum('hour'))['hour__sum'] or 0
            suministro_consumido_hoy = Transaction.objects.filter(
                suministro__asset=asset,
                suministro__item__id=132,
                fecha=today,
                tipo='c'
            ).aggregate(total_consumed=Sum('cant'))['total_consumed'] or 0

            if total_horas_asset > 0 and suministro_consumido_hoy > 0:
                horas_hoy = Decimal(horas_hoy)
                total_horas_asset = Decimal(total_horas_asset)
                consumo_historico_total = DailyFuelConsumption.objects.filter(
                    equipo__system__asset=asset,
                    fecha__gte=fecha_primer_reporte  # Filtrar desde la fecha del primer reporte
                ).aggregate(Sum('com_estimado_motor'))['com_estimado_motor__sum'] or 0

                consumo_historico_motor = DailyFuelConsumption.objects.filter(
                    equipo=equipo,
                    fecha__gte=fecha_primer_reporte
                ).aggregate(Sum('com_estimado_motor'))['com_estimado_motor__sum'] or 0

                # Calcular el factor de corrección
                if consumo_historico_total > 0 and len(equipos) > 1:
                    factor_correccion = consumo_historico_motor / consumo_historico_total
                else:
                    factor_correccion = Decimal(1) 

                consumo_estimado = (horas_hoy / total_horas_asset) * suministro_consumido_hoy * factor_correccion
                DailyFuelConsumption.objects.update_or_create(equipo=equipo, fecha=today, defaults={'com_estimado_motor': consumo_estimado})

@receiver(pre_save)
def track_model_changes_pre_save(sender, instance, **kwargs):
    # Solo rastrear los modelos que tienen el campo modified_by
    if hasattr(instance, 'modified_by'):
        # Almacenar los valores anteriores
        if instance.pk:  # Solo si el objeto ya existe
            try:
                instance._original_state = sender.objects.get(pk=instance.pk)
            except sender.DoesNotExist:
                instance._original_state = None

@receiver(post_save)
def track_model_changes_post_save(sender, instance, **kwargs):
    try:
        if hasattr(instance, 'modified_by'):
            # Si hay un estado anterior guardado en pre_save
            if hasattr(instance, '_original_state') and instance._original_state:
                original_instance = instance._original_state
                # Comparar los campos modificados
                for field in instance._meta.fields:
                    field_name = field.name
                    old_value = getattr(original_instance, field_name)
                    new_value = getattr(instance, field_name)

                    if old_value != new_value:  # Si el valor cambió
                        # Guardar en el registro de actividad
                        ActivityLog.objects.create(
                            user_name=instance.modified_by.username,
                            action='updated',
                            model_name=sender.__name__,
                            object_id=instance.pk,
                            field_name=field_name,
                            old_value=str(old_value),
                            new_value=str(new_value),
                            timestamp=timezone.now()
                        )
            else:
                # Si es una creación
                ActivityLog.objects.create(
                    user_name=instance.modified_by.username,
                    action='created',
                    model_name=sender.__name__,
                    object_id=instance.pk,
                    timestamp=timezone.now()
                )
    except AttributeError:
        # Si falta algún atributo (por ejemplo, 'modified_by'), no se hace nada
        pass
    except Exception as e:
        # Manejar otros errores si es necesario (registro en logs, etc.)
        pass

@receiver(pre_delete)
def track_model_deletion(sender, instance, **kwargs):
    # Solo rastrear los modelos que tienen el campo modified_by
    if hasattr(instance, 'modified_by'):
        # Guardar el registro de eliminación
        ActivityLog.objects.create(
            user_name=instance.modified_by.username if instance.modified_by else "Unknown",
            action='deleted',
            model_name=sender.__name__,
            object_id=instance.pk,
            timestamp=timezone.now()
        )

@receiver(post_save, sender=Ruta)
def update_asset_compliance_after_ruta_save(sender, instance, **kwargs):
    """
    Cada vez que se guarde un Ruta, actualizamos el compliance del Asset
    relacionado con su 'system'.
    """
    system = instance.system
    if system and system.asset:
        system.asset.update_maintenance_compliance_cache()

@receiver(post_save, sender=HistoryHour)
def update_asset_compliance_after_hours_save(sender, instance, **kwargs):
    """
    Cada vez que se guarde un HistoryHour, recalculamos el compliance 
    del Asset relacionado con equipo->system->asset.
    """
    equipo = instance.component
    if equipo and equipo.system and equipo.system.asset:
        equipo.system.asset.update_maintenance_compliance_cache()


@receiver(post_save, sender=Ot)
def update_asset_compliance_after_ot_save(sender, instance, **kwargs):
    """
    Cada vez que se guarde una OT, recalculamos el compliance 
    del Asset relacionado con su 'system'.
    Opcional: filtrar si solo quieres recalcular cuando la OT esté finalizada, etc.
    """
    system = instance.system
    if system and system.asset:
        # Ejemplo: recalcular solo si la OT está finalizada
        # if instance.state == 'f':
        #     system.asset.update_maintenance_compliance_cache()

        # O recalcular siempre que se guarde
        if instance.state == 'f':
            system.asset.update_maintenance_compliance_cache()