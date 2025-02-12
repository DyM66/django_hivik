# mto/views.py
import calendar
from calendar import month_name
from datetime import date
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from got.models import Asset
from .models import MaintenancePlan, MaintenancePlanEntry

class MaintenancePlanReportView(TemplateView):
    template_name = "mto/plan_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Suponemos que la URL envía el asset_abbr, por ejemplo: /mto/report/<asset_abbr>/
        asset_abbr = self.kwargs.get("asset_abbr")
        asset = get_object_or_404(Asset, abbreviation=asset_abbr)
        context["asset"] = asset

        # Obtener todos los planes de mantenimiento asociados a este asset.
        plans = MaintenancePlan.objects.filter(ruta__system__asset=asset).order_by("ruta__name")
        context["plans"] = plans

        if plans.exists():
            # Asumiremos que para el asset se está usando un mismo período para todos los planes.
            # Tomamos el período del primer plan.
            plan0 = plans.first()
            period_start = plan0.period_start
            period_end = plan0.period_end
            context["period_start"] = period_start
            context["period_end"] = period_end

            # Generar una lista de meses en el período.
            # Cada elemento será una tupla: (year, month, "NombreMes Año")
            months = []
            current = period_start.replace(day=1)
            while current <= period_end:
                label = f"{calendar.month_name[current.month]} {current.year}"
                months.append((current.year, current.month, label))
                # Avanzar al primer día del siguiente mes
                if current.month == 12:
                    current = date(current.year + 1, 1, 1)
                else:
                    current = date(current.year, current.month + 1, 1)
            context["months"] = months

            # Para cada plan, construir una estructura con el número de ejecuciones planificadas
            plan_rows = []
            for plan in plans:
                # Obtener todas las entradas (MaintenancePlanEntry) de este plan
                entries = plan.entries.all()
                # Creamos un diccionario que mapea (year, month) -> (planned_executions, actual_executions)
                entry_dict = {
                    (entry.year, entry.month): (entry.planned_executions, entry.actual_executions)
                    for entry in entries
                }
                # Para cada mes en la lista, obtenemos la tupla; si no existe, se asume (0,0)
                executions = [entry_dict.get((year, month), (0, 0)) for (year, month, _) in months]
                plan_rows.append({
                    "routine_name": plan.ruta.name,
                    "plan": plan,
                    "executions": executions,
                })

            context["plan_rows"] = plan_rows
        else:
            context["months"] = []
            context["plan_rows"] = []
        return context
