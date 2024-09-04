from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import HistoryHour, TransaccionSuministro, DailyFuelConsumption, Equipo, Item
from django.db.models import Avg, Sum, Min
from decimal import Decimal
from datetime import datetime

@receiver(post_save, sender=HistoryHour)
@receiver(post_delete, sender=HistoryHour)
def update_equipo_horometro(sender, instance, **kwargs):
    equipo = instance.component

    ultimos_30_registros = HistoryHour.objects.filter(
        component=equipo).order_by('-report_date')[:10]

    # Calcula el promedio de horas de los últimos 30 registros.
    promedio_horas = ultimos_30_registros.aggregate(
        promedio_horas=Avg('hour'))['promedio_horas']

    equipo.prom_hours = promedio_horas or 0
    equipo.horometro = equipo.calculate_horometro()
    equipo.save()
    update_fuel_consumption_for_asset(equipo, instance.report_date)


def update_fuel_consumption_for_asset(equipo, fecha):
    asset = equipo.system.asset
    
    # Obtener todos los equipos tipo 'r' (Motor a combustión) del asset
    equipos = Equipo.objects.filter(system__asset=asset, tipo='r')

    fecha_primer_reporte = TransaccionSuministro.objects.filter(
        suministro__asset=asset,
        suministro__item__id=132  # ID del combustible
    ).aggregate(primer_fecha=Min('fecha'))['primer_fecha']    

    # Obtener las horas totales del asset en la fecha dada
    total_horas_asset = HistoryHour.objects.filter(
        component__system__asset=asset,
        report_date=fecha
    ).aggregate(Sum('hour'))['hour__sum'] or 0

    suministro_combustible = TransaccionSuministro.objects.filter(
        suministro__asset=asset,
        suministro__item__id=132,
        fecha__date=fecha
    ).aggregate(Sum('cantidad_consumida'))['cantidad_consumida__sum'] or 0

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
                DailyFuelConsumption.objects.update_or_create(
                    equipo=equipo,
                    fecha=fecha,
                    defaults={'com_estimado_motor': consumo_estimado}
                )


@receiver(post_save, sender=TransaccionSuministro)
def create_daily_fuel_consumption(sender, instance, **kwargs):
    suministro = instance.suministro

    if suministro.item.id == 132:  # ID del combustible
        asset = suministro.asset

        fecha_primer_reporte = TransaccionSuministro.objects.filter(
            suministro__asset=asset,
            suministro__item__id=132  # ID del combustible
        ).aggregate(primer_fecha=Min('fecha'))['primer_fecha']  

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
            suministro_consumido_hoy = TransaccionSuministro.objects.filter(
                suministro__asset=asset,
                suministro__item__id=132,
                fecha__date=today
            ).aggregate(Sum('cantidad_consumida'))['cantidad_consumida__sum'] or 0

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
                DailyFuelConsumption.objects.update_or_create(
                    equipo=equipo,
                    fecha=today,
                    defaults={'com_estimado_motor': consumo_estimado}
                )