# mto/views.py
import calendar

from datetime import date, datetime
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.db import models
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import generic
from django.utils import timezone

from got.models import Asset, Suministro, Equipo, Ruta
from got.utils import get_full_systems_ids
from mto.utils import update_future_plan_entries_for_asset, get_filtered_rutas
from .models import MaintenancePlan, MaintenancePlanEntry

TODAY = timezone.now().date()


class AssetMaintenancePlanView(LoginRequiredMixin, generic.DetailView):
    model = Asset
    template_name = 'mto/asset_maintenance_plan.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        main, planned, exec, realized, filter_date = get_filtered_rutas(self.get_object(), self.request.GET)

        ubicaciones = set()
        usuarios = set()
        niveles = set()
        
        for r in planned:
            if r.equipo and r.equipo.ubicacion:  # Ubicación desde el equipo, si existe
                ubicaciones.add(r.equipo.ubicacion)
            else:
                r.ubic_label = "(sin)"
            
            for task in r.task_set.all():  # Usuarios: extraer de las actividades relacionadas a la ruta
                if task.responsible:
                    usuarios.add(task.responsible.get_full_name())
            # Niveles
            niveles.add(r.nivel)

        context['filter_date_str'] = filter_date.strftime('%Y-%m-%d')
        context['ubicaciones'] = sorted(ubicaciones)
        context['usuarios_unicos'] = sorted(usuarios)
        context['niveles_opciones'] = [(1, "Nivel 1 - Operadores"), (2, "Nivel 2 - Técnico"), (3, "Nivel 3 - Proveedor especializado")]
        context['mes'] = calendar.month_name[filter_date.month]
        context['planning'] = planned
        context['exec'] = exec
        context['realized'] = realized
        context['rotativos'] = Equipo.objects.filter(system__in=get_full_systems_ids(self.get_object(), self.request.user), tipo='r').exists()

        pm = MaintenancePlan.objects.filter(ruta__system__asset=self.get_object(), period_start__lte=TODAY, period_end__gte=TODAY).order_by("ruta")     
        
        if pm.exists():
            aggregated = pm.aggregate(min_start=models.Min('period_start'), max_end=models.Max('period_end'))
            period_start = aggregated['min_start']
            period_end = aggregated['max_end']   

            context["pm"] = pm
            context["period_start"] = period_start
            context["period_end"] = period_end

            # Calcular la cantidad de meses entre period_start y period_end:
            n_months = (period_end.year - period_start.year) * 12 + (period_end.month - period_start.month) + 1

            months = [
                (period_start.year + (period_start.month - 1 + i) // 12, ((period_start.month - 1 + i) % 12) + 1, f"{calendar.month_name[((period_start.month - 1 + i) % 12) + 1]} {period_start.year + (period_start.month - 1 + i) // 12}")
                for i in range(n_months)
            ]

            try:
                current_month_index = next(i for i, (year, month, _) in enumerate(months) if year == TODAY.year and month == TODAY.month)
            except StopIteration:
                current_month_index = None

            context["months"] = months
            context["current_month"] = current_month_index

            # Para cada plan, construir la estructura de ejecuciones
            plan_rows = []
            for plan in pm:
                entries = plan.entries.all()
                entry_dict = {
                    (entry.year, entry.month): (entry.planned_executions, entry.actual_executions) for entry in entries
                }
                executions = [entry_dict.get((year, month), (0, 0)) for (year, month, _) in months] # ¿???
                # Calcular totales acumulados sobre el período:
                total_planned = sum(x[0] for x in executions)
                total_actual = sum(x[1] for x in executions)
                plan_rows.append({
                    "routine_name": plan.ruta.name,
                    "plan": plan,
                    "executions": executions,
                    "total": (total_planned, total_actual),
                })
            context["plan_rows"] = plan_rows
        return context


@login_required
@user_passes_test(lambda u: u.is_superuser)  # Solo administradores, por ejemplo
def update_plan_entries_view(request, asset_abbr):
    asset = Asset.objects.get(abbreviation=asset_abbr)
    update_future_plan_entries_for_asset(asset)
    return HttpResponse("Plan entries actualizadas para el asset " + asset_abbr)

class MaintenancePlanReportView(generic.TemplateView):
    template_name = "mto/plan_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset_abbr = self.kwargs.get("asset_abbr")
        asset = get_object_or_404(Asset, abbreviation=asset_abbr)
        context["asset"] = asset

        # Obtener todos los planes de mantenimiento asociados a este asset.
        plans = MaintenancePlan.objects.filter(ruta__system__asset=asset).order_by("ruta__name")
        context["plans"] = plans

        if plans.exists():
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
                # Calcular totales acumulados sobre el período:
                total_planned = sum(x[0] for x in executions)
                total_actual = sum(x[1] for x in executions)
                plan_rows.append({
                    "routine_name": plan.ruta.name,
                    "plan": plan,
                    "executions": executions,
                    "total": (total_planned, total_actual),
                })
            context["plan_rows"] = plan_rows
            
            reqs_dict = {}
            for plan in plans:
                if self.request.GET.get("month"):
                    entry = plan.entries.filter(
                        year=datetime.strptime(self.request.GET.get("month"), "%Y-%m").year,
                        month=datetime.strptime(self.request.GET.get("month"), "%Y-%m").month
                    ).first()
                    remaining_for_plan = (entry.planned_executions - entry.actual_executions) if entry else 0
                    executed_for_plan = entry.actual_executions if entry else 0
                else:
                    total_planned = plan.entries.aggregate(total=Sum('planned_executions'))["total"] or 0
                    total_actual = plan.entries.aggregate(total=Sum('actual_executions'))["total"] or 0
                    remaining_for_plan = total_planned - total_actual
                    executed_for_plan = total_actual

                # Solo se procesan los planes que tengan alguna ejecución (pendiente o realizada)
                if remaining_for_plan <= 0 and executed_for_plan <= 0:
                    continue

                for req in plan.ruta.requisitos.all():
                    if req.item:
                        key = f"item_{req.item.id}"
                        req_name = str(req.item)
                        unit_price = req.item.unit_price  # Tomamos el valor del campo unit_price
                        suministro = Suministro.objects.filter(asset=asset, item=req.item).first()
                    elif req.service:
                        key = f"service_{req.service.id}"
                        req_name = req.service.description
                        unit_price = req.service.unit_price
                        suministro = None
                    else:
                        key = f"desc_{req.descripcion}"
                        req_name = req.descripcion
                        unit_price = 0
                        suministro = None

                    effective_required = req.cantidad * remaining_for_plan
                    effective_executed = req.cantidad * executed_for_plan

                    if key in reqs_dict:
                        reqs_dict[key]["total_required"] += effective_required
                        reqs_dict[key]["total_executed"] += effective_executed
                    else:
                        reqs_dict[key] = {
                            "name": req_name,
                            "total_required": effective_required,
                            "total_executed": effective_executed,
                            "suministro_quantity": suministro.cantidad if suministro else None,
                            "unit_price": unit_price,
                        }
            requirements_summary = []
            grand_total_required = 0
            grand_total_executed = 0
            for req in reqs_dict.values():
                line_total_required = req["unit_price"] * req["total_required"]
                line_total_executed = req["unit_price"] * req["total_executed"]
                req["line_total_required"] = line_total_required
                req["line_total_executed"] = line_total_executed
                grand_total_required += line_total_required
                grand_total_executed += line_total_executed
                requirements_summary.append(req)
            context["requirements_summary"] = requirements_summary
            context["grand_total_required"] = grand_total_required
            context["grand_total_executed"] = grand_total_executed

            # --- Rutinas Ejecutadas ---
            executed_routines = []
            for plan in plans:
                for entry in plan.entries.all():
                    # Si se filtra por mes, considerar solo la entrada correspondiente
                    if self.request.GET.get("month"):
                        filter_date = datetime.strptime(self.request.GET.get("month"), "%Y-%m").date()
                        if entry.year != filter_date.year or entry.month != filter_date.month:
                            continue
                    if entry.actual_executions <= 0:
                        continue
                    routine_cost = 0
                    req_details = []
                    for req in plan.ruta.requisitos.all():
                        # Se usa req.costo si es distinto de 0; de lo contrario, se usa el unit_price del item o servicio.
                        if req.item:
                            unit_cost = req.costo if req.costo != 0 else req.item.unit_price
                            req_name = str(req.item)
                        elif req.service:
                            unit_cost = req.costo if req.costo != 0 else req.service.unit_price
                            req_name = req.service.description
                        else:
                            unit_cost = req.costo if req.costo != 0 else 0
                            req_name = req.descripcion
                        cost_for_req = unit_cost * req.cantidad * entry.actual_executions
                        routine_cost += cost_for_req
                        req_details.append({
                            "name": req_name,
                            "quantity": req.cantidad,
                            "unit_cost": unit_cost,
                            "line_total": unit_cost * req.cantidad,
                        })
                    execution_date = date(entry.year, entry.month, 1)
                    executed_routines.append({
                        "execution_date": execution_date,
                        "routine_code": plan.ruta.code,
                        "routine_cost": routine_cost,
                        "actual_executions": entry.actual_executions,
                        "req_details": req_details,
                    })
            context["executed_routines"] = executed_routines

        else:
            context["months"] = []
            context["plan_rows"] = []
            context["current_month_index"] = None
            context["requirements_summary"] = []
            context["executed_routines"] = []
        return context


class MaintenancePlanDashboardView(generic.TemplateView):
    template_name = "mto/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # ===============================
        # 1. Obtener el asset a partir del parámetro 'asset_abbr'
        # ===============================
        asset_abbr = self.kwargs.get("asset_abbr")
        asset = get_object_or_404(Asset, abbreviation=asset_abbr)
        context["asset"] = asset

        # ===============================
        # 2. Procesar el parámetro opcional "month" (formato "YYYY-MM")
        # ===============================
        month_filter = self.request.GET.get("month")
        if month_filter:
            if month_filter == "all":
                filter_year = None
                filter_month = None
            else:
                try:
                    filter_date = datetime.strptime(month_filter, "%Y-%m").date()
                    filter_year = filter_date.year
                    filter_month = filter_date.month
                except ValueError:
                    filter_year = filter_month = None
        else:
            # Por defecto, se muestra el mes actual
            today = date.today()
            filter_year = today.year
            filter_month = today.month
        context["filter_year"] = filter_year
        context["filter_month"] = filter_month

        # ===============================
        # 3. Obtener los planes de mantenimiento asociados al asset
        # ===============================
        plans = MaintenancePlan.objects.filter(ruta__system__asset=asset).order_by("ruta__name")
        context["plans"] = plans

        # ===============================
        # 4. Generar la lista de meses del período (usando el primer plan)
        # ===============================
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

        # ===============================
        # 5. Calcular el "Resumen de Rutinas"
        #
        # Se recorre cada plan y se obtiene, ya sea para el mes filtrado o en total:
        # - Planificado y ejecutado.
        # Solo se incluyen aquellos planes con planificado > 0.
        # ===============================
        routine_rows = []
        grand_total_routine_cost = 0

        for plan in plans:
            if filter_year and filter_month:
                entry = plan.entries.filter(year=filter_year, month=filter_month).first()
                planned = entry.planned_executions if entry else 0
                actual = entry.actual_executions if entry else 0
            else:
                planned = plan.entries.aggregate(total=Sum('planned_executions'))["total"] or 0
                actual = plan.entries.aggregate(total=Sum('actual_executions'))["total"] or 0
                
            if planned == 0:
                continue

            pending = planned - actual
            finished_flag = planned <= actual

            # Calcular costo pendiente de la rutina:
            routine_cost = 0
            req_details = []
            for req in plan.ruta.requisitos.all():
                if req.item:
                    unit_cost = req.costo if req.costo != 0 else req.item.unit_price
                    req_name = str(req.item)
                elif req.service:
                    unit_cost = req.costo if req.costo != 0 else req.service.unit_price
                    req_name = req.service.description
                else:
                    unit_cost = req.costo if req.costo != 0 else 0
                    req_name = req.descripcion
                
                cost_for_req = unit_cost * req.cantidad * pending
                routine_cost += cost_for_req

                # Detalle para el modal
                req_details.append({
                    "name": req_name,
                    "quantity": req.cantidad,
                    "unit_cost": unit_cost,
                    "line_total": unit_cost * req.cantidad * pending,
                })

            grand_total_routine_cost += routine_cost

            routine_rows.append({
                "routine_name": plan.ruta.name,
                "level": plan.ruta.nivel,
                "planned": planned,
                "actual": actual,
                "pending": pending,
                "finished": finished_flag,
                "routine_cost": routine_cost,  # Costo pendiente de esta rutina
                "req_details": req_details,    # Detalle para el modal
                "routine_code": plan.ruta.code,
            })
        # Reordenar: primero las rutinas sin terminar y luego las terminadas
        unfinished = [r for r in routine_rows if not r["finished"]]
        finished = [r for r in routine_rows if r["finished"]]
        context["routine_rows"] = unfinished + finished
        context["grand_total_routine_cost"] = grand_total_routine_cost

        # ===============================
        # 6. Calcular "Rutinas Ejecutadas"
        #
        # Se recorren todas las entradas de cada plan. Si se especifica un filtro por mes,
        # se consideran únicamente las entradas del mes indicado.
        # Para cada entrada con ejecuciones (actual_executions > 0) se calcula:
        # - El costo total de la rutina, usando:
        #      unit_cost = req.costo (si distinto de 0) o, de lo contrario, el unit_price del item o service.
        # - Se arma una lista de detalles (para mostrar en el modal).
        #
        # La fecha de ejecución se guarda como el primer día del mes y se mostrará solo mes y año.
        # ===============================
        executed_routines = []
        for plan in plans:
            for entry in plan.entries.all():
                if filter_year and filter_month:
                    if entry.year != filter_year or entry.month != filter_month:
                        continue
                if entry.actual_executions <= 0:
                    continue
                # Para cada requerimiento de la rutina:
                # Si el campo costo es distinto de 0 se usa ese valor; de lo contrario se toma unit_price del artículo o servicio.
                routine_cost = 0
                req_details = []
                for req in plan.ruta.requisitos.all():
                    if req.item:
                        unit_cost = req.costo if req.costo != 0 else req.item.unit_price
                        req_name = str(req.item)
                    elif req.service:
                        unit_cost = req.costo if req.costo != 0 else req.service.unit_price
                        req_name = req.service.description
                    else:
                        unit_cost = req.costo if req.costo != 0 else 0
                        req_name = req.descripcion
                    cost_for_req = unit_cost * req.cantidad * entry.actual_executions
                    routine_cost += cost_for_req
                    req_details.append({
                        "name": req_name,
                        "quantity": req.cantidad,
                        "unit_cost": unit_cost,
                        "line_total": unit_cost * req.cantidad,
                    })
                # Se asume que la fecha de ejecución es el primer día del mes de la entrada
                execution_date = date(entry.year, entry.month, 1)
                executed_routines.append({
                    "execution_date": execution_date,
                    "routine_code": plan.ruta.name,
                    "routine_cost": routine_cost,
                    "actual_executions": entry.actual_executions,
                    "req_details": req_details,
                })
        context["executed_routines"] = executed_routines


        # ===============================
        # 7. Calcular desglose de requerimientos planificados por categoría
        #
        # Se agrupan los requerimientos (cantidad planificada = req.cantidad * (planificado - ejecutado))
        # en tres categorías:
        #    - "Consumibles": Items con seccion "c"
        #    - "Materiales/Repuestos": Items con seccion "h" o "r"
        #    - "Servicios": Requerimientos asociados a un Service.
        # ===============================
        requirements_breakdown = {
            "Consumibles": 0,
            "Materiales/Repuestos": 0,
            "Servicios": 0,
        }
        for plan in plans:
            if filter_year and filter_month:
                entry = plan.entries.filter(year=filter_year, month=filter_month).first()
                pending = (entry.planned_executions - entry.actual_executions) if entry else 0
            else:
                total_planned = plan.entries.aggregate(total=Sum('planned_executions'))["total"] or 0
                total_actual = plan.entries.aggregate(total=Sum('actual_executions'))["total"] or 0
                pending = total_planned - total_actual
            if pending <= 0:
                continue
            for req in plan.ruta.requisitos.all():
                if req.item:
                    unit_cost = req.costo if req.costo != 0 else req.item.unit_price
                    cost_for_req = unit_cost * req.cantidad * pending
                    if req.item.seccion == "c":
                        requirements_breakdown["Consumibles"] += cost_for_req
                    elif req.item.seccion in ["h", "r"]:
                        requirements_breakdown["Materiales/Repuestos"] += cost_for_req
                elif req.service:
                    unit_cost = req.costo if req.costo != 0 else req.service.unit_price
                    cost_for_req = unit_cost * req.cantidad * pending
                    requirements_breakdown["Servicios"] += cost_for_req
        context["requirements_breakdown"] = requirements_breakdown

        return context
    

class MaintenancePlanAllAssetsView(generic.TemplateView):
    template_name = "mto/maintenance_plan_all_assets.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filtrar assets que sean barcos (area = "a")
        assets = Asset.objects.filter(area="a").order_by("name")
        
        # Procesar el parámetro opcional "month":
        # Si se envía ?month=all se consideran TODOS los meses;
        # de lo contrario, por defecto se usa el mes actual.
        month_filter = self.request.GET.get("month")
        if month_filter:
            if month_filter == "all":
                filter_year = None
                filter_month = None
            else:
                try:
                    filter_date = datetime.strptime(month_filter, "%Y-%m").date()
                    filter_year = filter_date.year
                    filter_month = filter_date.month
                except ValueError:
                    filter_year = filter_month = None
        else:
            today = date.today()
            filter_year = today.year
            filter_month = today.month
        context["filter_year"] = filter_year
        context["filter_month"] = filter_month

        assets_data = []  # Lista para almacenar la información agrupada por asset
        
        # Para cada asset, obtener sus planes de mantenimiento CON rutinas de nivel 3
        for asset in assets:
            plans = MaintenancePlan.objects.filter(ruta__system__asset=asset, ruta__nivel=3).order_by("ruta__name")
            if not plans.exists():
                continue  # Omitir assets sin planes de mantenimiento (con nivel 3)
            asset_dict = {"asset": asset}
            
            # --- Reporte de "Resumen de Rutinas" para este asset ---
            routine_rows = []
            grand_total_routine_cost = 0
            for plan in plans:
                # Si se filtra por mes, usamos la entrada de ese mes; de lo contrario, acumulamos en total.
                if filter_year and filter_month:
                    entry = plan.entries.filter(year=filter_year, month=filter_month).first()
                    planned = entry.planned_executions if entry else 0
                    actual = entry.actual_executions if entry else 0
                else:
                    planned = plan.entries.aggregate(total=Sum('planned_executions'))["total"] or 0
                    actual = plan.entries.aggregate(total=Sum('actual_executions'))["total"] or 0
                if planned == 0:
                    continue
                pending = planned - actual
                # Calcular costo pendiente de la rutina
                routine_cost = 0
                for req in plan.ruta.requisitos.all():
                    if req.item:
                        unit_cost = req.costo if req.costo != 0 else req.item.unit_price
                    elif req.service:
                        unit_cost = req.costo if req.costo != 0 else req.service.unit_price
                    else:
                        unit_cost = req.costo if req.costo != 0 else 0
                    routine_cost += unit_cost * req.cantidad * pending
                grand_total_routine_cost += routine_cost
                routine_rows.append({
                    "routine_name": plan.ruta.name,
                    "level": plan.ruta.nivel,
                    "planned": planned,
                    "actual": actual,
                    "pending": pending,
                    "cost": routine_cost,
                    "routine_code": plan.ruta.code,
                })
            asset_dict["routine_rows"] = routine_rows
            asset_dict["grand_total_routine_cost"] = grand_total_routine_cost

            # --- Reporte de Plan de Mantenimiento (Cronograma) para este asset ---
            report_rows = []
            # Generar lista de meses usando el período del primer plan
            plan0 = plans.first()
            asset_months = []
            current = plan0.period_start.replace(day=1)
            while current <= plan0.period_end:
                label = f"{calendar.month_name[current.month]} {current.year}"
                month_param = f"{current.year}-{current.month:02d}"
                asset_months.append((current.year, current.month, label, month_param))
                if current.month == 12:
                    current = date(current.year+1, 1, 1)
                else:
                    current = date(current.year, current.month+1, 1)
            asset_dict["months"] = asset_months

            for plan in plans:
                entries = plan.entries.all()
                entry_dict = { (entry.year, entry.month): (entry.planned_executions, entry.actual_executions)
                               for entry in entries }
                executions = [ entry_dict.get((year, month), (0, 0)) for (year, month, _, _) in asset_months ]
                total_planned = sum(x[0] for x in executions)
                total_actual = sum(x[1] for x in executions)
                report_rows.append({
                    "routine_name": plan.ruta.name,
                    "executions": executions,
                    "total": (total_planned, total_actual),
                })
            asset_dict["report_rows"] = report_rows

            # --- Rutinas Ejecutadas para este asset ---
            executed_routines = []
            for plan in plans:
                for entry in plan.entries.all():
                    if filter_year and filter_month:
                        if entry.year != filter_year or entry.month != filter_month:
                            continue
                    if entry.actual_executions <= 0:
                        continue
                    routine_cost = 0
                    for req in plan.ruta.requisitos.all():
                        if req.item:
                            unit_cost = req.costo if req.costo != 0 else req.item.unit_price
                        elif req.service:
                            unit_cost = req.costo if req.costo != 0 else req.service.unit_price
                        else:
                            unit_cost = req.costo if req.costo != 0 else 0
                        routine_cost += unit_cost * req.cantidad * entry.actual_executions
                    executed_routines.append({
                        "execution_date": date(entry.year, entry.month, 1),
                        "routine_code": plan.ruta.code,
                        "routine_cost": routine_cost,
                        "actual_executions": entry.actual_executions,
                    })
            asset_dict["executed_routines"] = executed_routines

            # --- Desglose de Requerimientos (por costos) para este asset ---
            requirements_breakdown = {
                "Consumibles": 0,
                "Materiales/Repuestos": 0,
                "Servicios": 0,
            }
            for plan in plans:
                if filter_year and filter_month:
                    entry = plan.entries.filter(year=filter_year, month=filter_month).first()
                    pending = (entry.planned_executions - entry.actual_executions) if entry else 0
                else:
                    total_planned = plan.entries.aggregate(total=Sum('planned_executions'))["total"] or 0
                    total_actual = plan.entries.aggregate(total=Sum('actual_executions'))["total"] or 0
                    pending = total_planned - total_actual
                if pending <= 0:
                    continue
                for req in plan.ruta.requisitos.all():
                    if req.item:
                        unit_cost = req.costo if req.costo != 0 else req.item.unit_price
                        cost_for_req = unit_cost * req.cantidad * pending
                        if req.item.seccion == "c":
                            requirements_breakdown["Consumibles"] += cost_for_req
                        elif req.item.seccion in ["h", "r"]:
                            requirements_breakdown["Materiales/Repuestos"] += cost_for_req
                    elif req.service:
                        unit_cost = req.costo if req.costo != 0 else req.service.unit_price
                        cost_for_req = unit_cost * req.cantidad * pending
                        requirements_breakdown["Servicios"] += cost_for_req
            asset_dict["requirements_breakdown"] = requirements_breakdown

            assets_data.append(asset_dict)
        context["assets_data"] = assets_data
        return context


from django.views.generic import TemplateView
from django.utils import timezone
from django.db.models import Count, Q
from django.utils.text import Truncator
from got.models import Asset, Ot, Task, Ruta, FailureReport
from inv.models import Solicitud 
from collections import defaultdict


class ScrollytellingAssetsView(TemplateView):
    template_name = "mto/scrollytelling.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_date = timezone.now().date()
        assets = Asset.objects.filter(area='a', show=True)
        assets_data = []
        assets_with_ot = []
        
        for asset in assets:
            ots_en_ejecucion = Ot.objects.filter(system__asset=asset, state='x')
            if not ots_en_ejecucion.exists():
                continue  # Omitir assets sin OT en ejecución de la sección principal

            ot_ejecucion_data = []  # Procesar OT en ejecución
            for ot in ots_en_ejecucion:
                tasks_pending = ot.task_set.filter(finished=False)
                ot_ejecucion_data.append({'ot': ot, 'tasks': tasks_pending,})

            # OT finalizadas (estado "f") del mes actual
            ots_finalizadas = Ot.objects.filter(system__asset=asset, state='f', closing_date__year=current_date.year, closing_date__month=current_date.month)
            
            # Repasamos ordenes de trabajo que contienen codigos de rutinas en la descrición
            routines_codes = list(asset.system_set.values_list('rutas__code', flat=True))
            ot_finalizadas_grouped = {}
            for ot in ots_finalizadas:
                if any(code and str(code) in ot.description for code in routines_codes):
                    key = ot.description  # Agrupamos por descripción (ajustable)
                    if key in ot_finalizadas_grouped:
                        ot_finalizadas_grouped[key]['count'] += 1
                    else:
                        ot_finalizadas_grouped[key] = {'ot': ot, 'count': 1}
            ots_finalizadas_list = list(ot_finalizadas_grouped.values())

            # Indicadores de fallas
            # Se consideran todos los FailureReport relacionados a un equipo cuyo sistema pertenezca a este asset.
            failure_reports = FailureReport.objects.filter(equipo__system__asset=asset)
            total_failure_reports = failure_reports.count()
            critical_failure_reports = failure_reports.filter(critico=True).count()
            
            # Solicitudes asociadas a las OT en ejecución, ordenadas por número de OT
            solicitudes_qs = Solicitud.objects.filter(ot__in=ots_en_ejecucion).order_by('ot__num_ot')
            solicitudes_data = []
            for sol in solicitudes_qs:
                if sol.ot:
                    cotizacion = f"{sol.ot.description} - {sol.quotation if sol.quotation else Truncator(sol.suministros).chars(50)}"
                    ot_num = sol.ot.num_ot
                else:
                    cotizacion = Truncator(sol.suministros).chars(50)
                    ot_num = None
                solicitudes_data.append({
                    'cotizacion': cotizacion,
                    'ot_num': ot_num,
                    'num_sc': sol.num_sc if sol.num_sc else "-",
                    'total': sol.total,
                    'estado': sol.recibido_por,
                    'suministros': sol.suministros,
                    'solicitante': sol.requested_by,
                    'creation_date': sol.creation_date,
                    'id': sol.id,
                    'quotation_url': sol.quotation_file.url if sol.quotation_file else "",
                    'total_numeric': sol.total,
                    'grouped': False,  # Por defecto, se considerará individual
                })

            # Agrupar aquellas solicitudes cuyo total es inferior a 200000 y pertenecen a una OT
            grouped_dict = defaultdict(lambda: {'solicitudes': [], 'count': 0, 'sc_numbers': [], 'subtotal': 0})
            individual_solicitudes = []
            for sol in solicitudes_data:
                if sol['total_numeric'] < 2000000 and sol['ot_num'] is not None:
                    group = grouped_dict[sol['ot_num']]
                    group['solicitudes'].append(sol)
                    group['count'] += 1
                    group['sc_numbers'].append(sol['num_sc'])
                    group['ot_description'] = sol['cotizacion'] #.split(' - ')[0]
                    group['ot_num'] = sol['ot_num']
                    group['subtotal'] += sol['total_numeric']
                else:
                    individual_solicitudes.append(sol)
            # Si un grupo tiene solo una solicitud, la tratamos como individual
            final_grouped = []
            for key, group in grouped_dict.items():
                if group['count'] == 1:
                    individual_solicitudes.append(group['solicitudes'][0])
                else:
                    for sol in group['solicitudes']:
                        sol['grouped'] = True
                    final_grouped.append(group)

            individual_total = sum(sol['total_numeric'] for sol in individual_solicitudes)
            grouped_total = sum(group['subtotal'] for group in final_grouped)
            overall_total = individual_total + grouped_total

            assets_data.append({
                'asset': asset,
                'compliance': asset.maintenance_compliance_cache,
                'ots_ejecucion': ot_ejecucion_data,
                'ots_finalizadas': ots_finalizadas_list,
                'failure_reports_total': total_failure_reports,
                'failure_reports_critical': critical_failure_reports,
                'grouped_solicitudes': final_grouped,
                'individual_solicitudes': individual_solicitudes,
                'overall_total': overall_total,
            })

            assets_with_ot.append(asset)
        assets_no_ot = assets.exclude(pk__in=[a.pk for a in assets_with_ot]) # Assets sin OT en ejecución: se muestran en la sección final
        
        context['assets_data'] = assets_data
        context['assets_no_ot'] = assets_no_ot
        context['current_date'] = current_date
        context['page_title'] = "Mantenimiento"

        labels = ['Preventivo', 'Correctivo', 'Modificativo']
        ots = Ot.objects.filter(creation_date__month=current_date.month, creation_date__year=current_date.year, system__asset__area='a')
        total_ot = ots.count()
        if total_ot > 0:
            count_preventivo = ots.filter(tipo_mtto='p').count()
            count_correctivo = ots.filter(tipo_mtto='c').count()
            count_modificativo = ots.filter(tipo_mtto='m').count()
            pct_preventivo = round((count_preventivo / total_ot) * 100, 2)
            pct_correctivo = round((count_correctivo / total_ot) * 100, 2)
            pct_modificativo = round((count_modificativo / total_ot) * 100, 2)
        else:
            count_preventivo = count_correctivo = count_modificativo = 0
            pct_preventivo = pct_correctivo = pct_modificativo = 0

        ot_chart = {
            'preventivo_count': count_preventivo,
            'correctivo_count': count_correctivo,
            'modificativo_count': count_modificativo,
            'preventivo_pct': round(pct_preventivo, 2),
            'correctivo_pct': round(pct_correctivo, 2),
            'modificativo_pct': round(pct_modificativo, 2),
        }

        context['labels'] = labels
        context['data'] = ot_chart


        # NUEVO BLOQUE: Tabla de mantenimiento
        months = list(range(2, 13))
        month_names = ["Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

        context['cu_month'] = month_names[current_date.month - 2]

        maintenance_table = {}
        # Configuración de filas: cada entrada define el área y el campo a sumar
        rows_config = [
            {"label": "Mantenimiento Embarcaciones Programados", "area": "a", "field": "planned_executions"},
            {"label": "Mantenimiento Embarcaciones Ejecutados", "area": "a", "field": "actual_executions"},
            {"label": "Mantenimiento Equipos de BUCEO Programados", "area": "o", "field": "planned_executions"},
            {"label": "Mantenimiento Equipos de BUCEO Ejecutados", "area": "o", "field": "actual_executions"},
            {"label": "Mantenimiento VEHICULOS Programados", "area": "v", "field": "planned_executions"},
            {"label": "Mantenimiento VEHICULOS Ejecutados", "area": "v", "field": "actual_executions"},
        ]
        # Para cada fila, calcular los totales mes a mes
        for row in rows_config:
            row_values = []
            for m in months:
                agg = MaintenancePlanEntry.objects.filter(
                    plan__ruta__system__asset__area=row["area"],
                    month=m,
                    year=current_date.year
                ).aggregate(total=Sum(row["field"]))
                value = agg["total"] or 0
                row_values.append(value)
            maintenance_table[row["label"]] = row_values

        # Fila final: porcentaje de ejecución = (total ejecutado / total planificado * 100)
        total_percentage = []
        for m in months:
            agg_planned = MaintenancePlanEntry.objects.filter(
                plan__ruta__system__asset__area__in=['a', 'o', 'v'],
                month=m, year=current_date.year).aggregate(total=Sum("planned_executions"))
            planned = agg_planned["total"] or 0

            agg_executed = MaintenancePlanEntry.objects.filter(
                plan__ruta__system__asset__area__in=['a', 'o', 'v'],
                month=m, year=current_date.year).aggregate(total=Sum("actual_executions"))
            executed = agg_executed["total"] or 0

            percentage = (executed / planned * 100) if planned > 0 else 0
            total_percentage.append(round(percentage, 2))
        maintenance_table["Total (%)"] = total_percentage

        context['maintenance_table'] = maintenance_table
        context['maintenance_months'] = month_names

        # INDICADOR GLOBAL: Cálculo del promedio de maintenance_compliance_cache
        # Por ejemplo, de todos los assets con show=True que tengan un valor en el campo.
        from django.db.models import Avg
        all_assets = Asset.objects.filter(show=True).exclude(maintenance_compliance_cache__isnull=True)
        avg_compliance = all_assets.aggregate(Avg('maintenance_compliance_cache'))
        # Si no hay registros, usar 0 o None
        global_compliance = avg_compliance['maintenance_compliance_cache__avg'] or 0
        # Redondear a 2 decimales
        context['global_maintenance_compliance'] = round(global_compliance, 2)

        # NUEVO: Rutinas planeadas vs ejecutadas por cada barco (año actual)
        assets_bar_data = []
        barcos = Asset.objects.filter(area='a', show=True)
        for barco in barcos:
            agg_bar = MaintenancePlanEntry.objects.filter(
                plan__ruta__system__asset=barco,
                year=current_date.year,
                month=current_date.month
            ).aggregate(
                planned=Sum('planned_executions'),
                executed=Sum('actual_executions')
            )
            planned_val = agg_bar['planned'] or 0
            executed_val = agg_bar['executed'] or 0
            assets_bar_data.append({
                'name': barco.name,
                'planned': planned_val,
                'executed': executed_val,
            })

        context['assets_bar_data'] = assets_bar_data

        return context


from mto.forms import SolicitudUpdateForm
from django.urls import reverse_lazy
from django.views.generic import UpdateView
class EditSolicitudView(LoginRequiredMixin, UpdateView):
    model = Solicitud
    form_class = SolicitudUpdateForm
    template_name = "mto/edit_solicitud.html"

    def get_success_url(self):
        # Redirigir al listado de solicitudes (ajusta según tus necesidades)
        return reverse_lazy('mto:stoytell')

