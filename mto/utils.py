# mto/utils.py
from datetime import timedelta, date
from got.models import Ruta
from mto.models import MaintenancePlan

def record_execution(plan, execution_date):
    """
    Registra una ejecución en el plan de mantenimiento 'plan' para la fecha 'execution_date'.

    Lógica:
      - Se obtienen todas las entradas del plan ordenadas por año y mes.
      - Si el total de ejecuciones reales (actual_executions) es menor que el total planificado,
        se recorre la secuencia y se asigna la ejecución a la primera entrada en la que no se haya cumplido la planificación.
      - Si el total real es mayor o igual al planificado, se intenta asignar la ejecución a la entrada cuyo
        año y mes coincida con 'execution_date'. Si no existe, se retorna False.
      
    Retorna True si se pudo registrar la ejecución; de lo contrario, False.
    """
    # Obtener las entradas del plan ordenadas por año y mes
    entries = plan.entries.all().order_by('year', 'month')
    total_planned = sum(entry.planned_executions for entry in entries)
    total_actual = sum(entry.actual_executions for entry in entries)
    
    if total_actual < total_planned:
        # Asignar la ejecución a la primera entrada que no haya alcanzado el planificado
        for entry in entries:
            if entry.actual_executions < entry.planned_executions:
                entry.actual_executions += 1
                entry.save()
                return True
    else:
        # Si se han cumplido (o superado) lo planificado, asignar la ejecución al mes de la fecha real
        try:
            entry = entries.get(year=execution_date.year, month=execution_date.month)
            entry.actual_executions += 1
            entry.save()
            return True
        except entries.model.DoesNotExist:
            # No existe entrada para el mes de execution_date; se podría registrar la ejecución "extra" o retornar False.
            return False


def calculate_execution_dates(ruta, plan_start_date, period_end):
    """Calcula todas las fechas planificadas desde plan_start_date hasta period_end para una ruta."""
    execution_dates = []
    if ruta.control == 'd':
        # Para control en días: cada 'frecuency' días
        current_date = plan_start_date
        while current_date <= period_end:
            execution_dates.append(current_date)
            current_date += timedelta(days=ruta.frecuency)
    elif ruta.control == 'h':
        # Para control en horas: se toma la primera fecha planificada (propiedad next_date)
        first_date = ruta.next_date
        # Validar que prom_hours sea al menos 2
        prom = ruta.equipo.prom_hours if (ruta.equipo and ruta.equipo.prom_hours and ruta.equipo.prom_hours >= 2) else 2
        try:
            interval_days = int(ruta.frecuency / prom)
        except Exception:
            interval_days = 1
        if interval_days < 1:
            interval_days = 1
        current_date = first_date
        while current_date <= period_end:
            execution_dates.append(current_date)
            current_date += timedelta(days=interval_days)
    else:
        execution_dates = []
    return execution_dates

def update_future_plan_entries_for_asset(asset):
    """
    Para cada MaintenancePlan asociado a alguna ruta del asset,
    actualiza (recalcula) las entradas cuyos meses sean FUTUROS al mes actual.
    """
    today = date.today()
    current_year, current_month = today.year, today.month
    # Para cada ruta del asset:
    rutas = Ruta.objects.filter(system__asset=asset)
    for ruta in rutas:
        # Obtenemos el plan que ya esté activo para esa ruta; si hay más de uno, se actualiza cada uno
        plans = ruta.maintenance_plans.all()
        for plan in plans:
            # Solo actualizar entradas con mes/ año futuros
            # Primero, recalcular todas las fechas planificadas (desde la fecha de inicio del plan hasta el final del periodo)
            execution_dates = calculate_execution_dates(ruta, plan.start_count_date, plan.period_end)
            # Agrupar por (year, month)
            planned_by_month = {}
            for dt in execution_dates:
                key = (dt.year, dt.month)
                planned_by_month[key] = planned_by_month.get(key, 0) + 1
            # Ahora, para cada entrada del plan, si es de un mes futuro, actualizar el valor
            for entry in plan.entries.all():
                # Consideramos "futuro" si (entry.year, entry.month) es mayor que (current_year, current_month)
                if (entry.year > current_year) or (entry.year == current_year and entry.month > current_month):
                    new_planned = planned_by_month.get((entry.year, entry.month), 0)
                    if new_planned != entry.planned_executions:
                        entry.planned_executions = new_planned
                        entry.save()


# mto/utils.py (continuación)

def create_maintenance_plan_for_ruta(ruta, period_start, period_end):
    """
    Crea un MaintenancePlan para la ruta en el período especificado, junto con las entradas mensuales.
    Se utiliza la fecha actual de intervención (ruta.intervention_date) como la fecha de inicio de conteo.
    """
    # Evitar crear plan duplicado: si ya existe un plan para este rango, no crear.
    if ruta.maintenance_plans.filter(period_start=period_start, period_end=period_end).exists():
        return None

    plan = MaintenancePlan.objects.create(
        ruta=ruta,
        start_count_date=ruta.intervention_date,
        period_start=period_start,
        period_end=period_end
    )

    execution_dates = []
    if ruta.control == 'd':
        freq = ruta.frecuency
        current_date = plan.start_count_date
        while current_date <= period_end:
            if current_date >= period_start:
                execution_dates.append(current_date)
            current_date += timedelta(days=freq)
    elif ruta.control == 'h':
        first_date = ruta.next_date
        prom = ruta.equipo.prom_hours if (ruta.equipo and ruta.equipo.prom_hours and ruta.equipo.prom_hours >= 2) else 2
        try:
            interval_days = int(ruta.frecuency / prom)
        except Exception:
            interval_days = 1
        if interval_days < 1:
            interval_days = 1
        current_date = first_date
        while current_date <= period_end:
            if current_date >= period_start:
                execution_dates.append(current_date)
            current_date += timedelta(days=interval_days)
    else:
        execution_dates = []

    # Agrupar fechas por (year, month)
    planned_by_month = {}
    for dt in execution_dates:
        key = (dt.year, dt.month)
        planned_by_month[key] = planned_by_month.get(key, 0) + 1

    # Crear MaintenancePlanEntry para cada mes del período
    current = period_start
    while current <= period_end:
        key = (current.year, current.month)
        planned = planned_by_month.get(key, 0)
        from mto.models import MaintenancePlanEntry  # Import local para evitar circularidad
        MaintenancePlanEntry.objects.create(
            plan=plan,
            month=current.month,
            year=current.year,
            planned_executions=planned,
            actual_executions=0
        )
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    return plan

