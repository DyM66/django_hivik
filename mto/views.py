# mto/views.py
import calendar
from calendar import month_name
from datetime import date, datetime
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from got.models import Asset
from mto.utils import update_future_plan_entries_for_asset
from .models import MaintenancePlan, MaintenancePlanEntry
from collections import defaultdict
from django.db.models import Sum, Q
from got.models import Suministro


@login_required
@user_passes_test(lambda u: u.is_superuser)  # Solo administradores, por ejemplo
def update_plan_entries_view(request, asset_abbr):
    asset = Asset.objects.get(abbreviation=asset_abbr)
    update_future_plan_entries_for_asset(asset)
    return HttpResponse("Plan entries actualizadas para el asset " + asset_abbr)

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
            current_month_index = None  # Índice del mes actual dentro de la lista
            i = 0
            today = date.today()
            while current <= period_end:
                label = f"{calendar.month_name[current.month]} {current.year}"
                months.append((current.year, current.month, label))
                # Si el mes actual coincide con el mes y año de hoy, guardamos el índice
                if current.year == today.year and current.month == today.month:
                    current_month_index = i
                i += 1
                # Avanzar al primer día del siguiente mes
                if current.month == 12:
                    current = date(current.year + 1, 1, 1)
                else:
                    current = date(current.year, current.month + 1, 1)
            context["months"] = months
            context["current_month_index"] = current_month_index

            # Para cada plan, construir la estructura de ejecuciones
            plan_rows = []
            for plan in plans:
                entries = plan.entries.all()
                entry_dict = {
                    (entry.year, entry.month): (entry.planned_executions, entry.actual_executions)
                    for entry in entries
                }
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
            context["current_month_index"] = None
        return context


class MaintenancePlanDashboardView(TemplateView):
    template_name = "mto/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset_abbr = self.kwargs.get("asset_abbr")
        asset = get_object_or_404(Asset, abbreviation=asset_abbr)
        context["asset"] = asset

        # Parámetro opcional "month" en formato "YYYY-MM"
        month_filter = self.request.GET.get("month")
        if month_filter:
            try:
                filter_date = datetime.strptime(month_filter, "%Y-%m").date()
                filter_year = filter_date.year
                filter_month = filter_date.month
            except ValueError:
                filter_year = filter_month = None
        else:
            filter_year = None
            filter_month = None
        context["filter_year"] = filter_year
        context["filter_month"] = filter_month

        # Obtener planes de mantenimiento para este asset (ya filtrados por asset)
        plans = MaintenancePlan.objects.filter(ruta__system__asset=asset).order_by("ruta__name")
        context["plans"] = plans

        # Generar lista de meses según el período del primer plan (si existe)
        months = []
        spanish_months = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        if plans.exists():
            plan0 = plans.first()
            period_start = plan0.period_start
            period_end = plan0.period_end
            context["period_start"] = period_start
            context["period_end"] = period_end
            current = period_start.replace(day=1)
            current_month_index = None
            i = 0
            today = date.today()
            while current <= period_end:
                label = f"{spanish_months.get(current.month, current.month)} {current.year}"
                month_param = f"{current.year}-{current.month:02d}"
                months.append((current.year, current.month, label, month_param))
                if current.year == today.year and current.month == today.month:
                    current_month_index = i
                i += 1
                if current.month == 12:
                    current = date(current.year + 1, 1, 1)
                else:
                    current = date(current.year, current.month + 1, 1)
            context["months"] = months
            context["current_month_index"] = current_month_index
        else:
            context["months"] = []
            context["current_month_index"] = None

        # Resumen de rutinas (sin cambios respecto a lo anterior)
        routine_rows = []
        for plan in plans:
            if filter_year and filter_month:
                entry = plan.entries.filter(year=filter_year, month=filter_month).first()
                planned_for_month = entry.planned_executions if entry else 0
                actual_for_month = entry.actual_executions if entry else 0
                if planned_for_month == 0:
                    continue
                remaining = planned_for_month - actual_for_month
                finished_flag = planned_for_month <= actual_for_month
                routine_rows.append({
                    "routine_name": plan.ruta.name,
                    "level": plan.ruta.nivel,
                    "planned": planned_for_month,
                    "actual": actual_for_month,
                    "remaining": remaining,
                    "finished": finished_flag,
                })
            else:
                total_planned = plan.entries.aggregate(total=Sum('planned_executions'))["total"] or 0
                total_actual = plan.entries.aggregate(total=Sum('actual_executions'))["total"] or 0
                if total_planned == 0:
                    continue
                remaining = total_planned - total_actual
                finished_flag = total_planned <= total_actual
                routine_rows.append({
                    "routine_name": plan.ruta.name,
                    "level": plan.ruta.nivel,
                    "planned": total_planned,
                    "actual": total_actual,
                    "remaining": remaining,
                    "finished": finished_flag,
                })
        # Reordenar: primero las rutinas sin terminar y luego las terminadas
        unfinished = [r for r in routine_rows if not r["finished"]]
        finished = [r for r in routine_rows if r["finished"]]
        context["routine_rows"] = unfinished + finished

        reqs_dict = {}
        for plan in plans:
            if filter_year and filter_month:
                entry = plan.entries.filter(year=filter_year, month=filter_month).first()
                planned_multiplier = entry.planned_executions if entry else 0
            else:
                planned_multiplier = plan.entries.aggregate(total=Sum('planned_executions'))["total"] or 0

            if planned_multiplier:
                for req in plan.ruta.requisitos.all():
                    if req.item:
                        key = f"item_{req.item.id}"
                        req_name = str(req.item)
                        suministro = Suministro.objects.filter(asset=asset, item=req.item).first()
                    elif req.service:
                        key = f"service_{req.service.id}"
                        req_name = req.service.description
                        suministro = None
                    else:
                        key = f"desc_{req.descripcion}"
                        req_name = req.descripcion
                        suministro = None
                    if key in reqs_dict:
                        reqs_dict[key]["total_required_for_month"] += req.cantidad * planned_multiplier
                    else:
                        reqs_dict[key] = {
                            "name": req_name,
                            "total_required_for_month": req.cantidad * planned_multiplier,
                            "suministro_quantity": suministro.cantidad if suministro else None,
                        }
        # Incluir solo aquellos requerimientos con cantidad mayor a cero
        context["requirements_summary"] = [
            req for req in reqs_dict.values() if req["total_required_for_month"] > 0
        ]

        return context