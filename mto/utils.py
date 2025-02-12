# mto/utils.py
from datetime import date
from .models import MaintenancePlanEntry

def update_plan_executions(ruta, execution_date):
    """
    Dada una ruta y una fecha de ejecución, actualiza (incrementa en 1)
    la entrada del MaintenancePlanEntry correspondiente al mes y año de execution_date,
    siempre que exista un MaintenancePlan para la ruta cuyo período incluya esa fecha.
    """
    # Se busca un plan para la ruta cuyo período incluya la fecha de ejecución.
    plan = ruta.maintenance_plans.filter(period_start__lte=execution_date, period_end__gte=execution_date).first()
    if plan:
        entry = plan.entries.filter(year=execution_date.year, month=execution_date.month).first()
        if entry:
            entry.actual_executions += 1
            entry.save()
