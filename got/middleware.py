# middleware.py
import time
import logging

logger = logging.getLogger(__name__)

class RequestTimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        end_time = time.time()
        total_time = end_time - start_time
        logger.debug(f"Tiempo total de procesamiento del servidor: {total_time} segundos")
        return response


# def update_fuel_consumption_for_asset(equipo, fecha):
#     asset = equipo.system.asset
#     equipos = Equipo.objects.filter(system__asset=asset, tipo='r')

#     fecha_primer_reporte = Transaction.objects.filter(
#         suministro__asset=asset, suministro__item__id=132,  # ID del combustible
#         tipo='c').aggregate(primer_fecha=Min('fecha'))['primer_fecha']    

#     # Obtener las horas totales del asset en la fecha dada
#     total_horas_asset = HistoryHour.objects.filter(component__system__asset=asset, report_date=fecha).aggregate(Sum('hour'))['hour__sum'] or 0

#     suministro_combustible = Transaction.objects.filter(suministro__asset=asset, suministro__item__id=132, fecha=fecha, tipo='c').aggregate(total_consumed=Sum('cant'))['total_consumed'] or 0

#     if suministro_combustible > 0 and total_horas_asset > 0:
#         consumo_historico_total = DailyFuelConsumption.objects.filter(
#             equipo__system__asset=asset,
#             fecha__gte=fecha_primer_reporte  # Filtrar desde la fecha del primer reporte
#         ).aggregate(Sum('com_estimado_motor'))['com_estimado_motor__sum'] or 0

#         # Actualizar el consumo estimado para cada equipo
#         for equipo in equipos:
#             horas_hoy = HistoryHour.objects.filter(component=equipo, report_date=fecha).aggregate(Sum('hour'))['hour__sum'] or 0

#             if horas_hoy > 0:
#                 horas_hoy = Decimal(horas_hoy)
#                 total_horas_asset = Decimal(total_horas_asset)
#                 consumo_historico_motor = DailyFuelConsumption.objects.filter(
#                     equipo=equipo,
#                     fecha__gte=fecha_primer_reporte
#                 ).aggregate(Sum('com_estimado_motor'))['com_estimado_motor__sum'] or 0

#                 if consumo_historico_total > 0 and len(equipos) > 1:
#                     factor_correccion = consumo_historico_motor / consumo_historico_total
#                 else:
#                     factor_correccion = Decimal(1) 

#                 consumo_estimado = (horas_hoy / total_horas_asset) * suministro_combustible * factor_correccion

#                 # Actualizar o crear el registro de DailyFuelConsumption
#                 DailyFuelConsumption.objects.update_or_create(equipo=equipo, fecha=fecha, defaults={'com_estimado_motor': consumo_estimado})

# @receiver(post_save, sender=Transaction)
# def create_daily_fuel_consumption(sender, instance, **kwargs):
#     suministro = instance.suministro

#     if suministro.item.id == 132 and instance.tipo == 'c':  # ID del combustible
#         asset = suministro.asset

#         fecha_primer_reporte = Transaction.objects.filter(
#             suministro__asset=asset, suministro__item__id=132,  # ID del combustible
#             tipo='c').aggregate(primer_fecha=Min('fecha'))['primer_fecha']  

#         if isinstance(instance.fecha, str):
#             today = datetime.strptime(instance.fecha, '%Y-%m-%d').date()
#         else:
#             today = instance.fecha
        
#         equipos = Equipo.objects.filter(system__asset=asset, tipo='r')

#         for equipo in equipos:
#             horas_hoy = HistoryHour.objects.filter(component=equipo, report_date=today).aggregate(Sum('hour'))['hour__sum'] or 0
#             if horas_hoy == 0:
#                 continue
            
#             total_horas_asset = HistoryHour.objects.filter(component__system__asset=equipo.system.asset, report_date=today).aggregate(Sum('hour'))['hour__sum'] or 0
#             suministro_consumido_hoy = Transaction.objects.filter(
#                 suministro__asset=asset,
#                 suministro__item__id=132,
#                 fecha=today,
#                 tipo='c'
#             ).aggregate(total_consumed=Sum('cant'))['total_consumed'] or 0

#             if total_horas_asset > 0 and suministro_consumido_hoy > 0:
#                 horas_hoy = Decimal(horas_hoy)
#                 total_horas_asset = Decimal(total_horas_asset)
#                 consumo_historico_total = DailyFuelConsumption.objects.filter(
#                     equipo__system__asset=asset,
#                     fecha__gte=fecha_primer_reporte  # Filtrar desde la fecha del primer reporte
#                 ).aggregate(Sum('com_estimado_motor'))['com_estimado_motor__sum'] or 0

#                 consumo_historico_motor = DailyFuelConsumption.objects.filter(
#                     equipo=equipo,
#                     fecha__gte=fecha_primer_reporte
#                 ).aggregate(Sum('com_estimado_motor'))['com_estimado_motor__sum'] or 0

#                 # Calcular el factor de corrección
#                 if consumo_historico_total > 0 and len(equipos) > 1:
#                     factor_correccion = consumo_historico_motor / consumo_historico_total
#                 else:
#                     factor_correccion = Decimal(1) 

#                 consumo_estimado = (horas_hoy / total_horas_asset) * suministro_consumido_hoy * factor_correccion
#                 DailyFuelConsumption.objects.update_or_create(equipo=equipo, fecha=today, defaults={'com_estimado_motor': consumo_estimado})
