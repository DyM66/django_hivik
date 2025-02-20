# mto/views.py
import calendar

from datetime import date, datetime
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import generic

from got.models import Asset, Suministro, Equipo, Ruta
from got.utils import get_full_systems_ids
from got.forms import RutinaFilterForm
from mto.utils import update_future_plan_entries_for_asset, get_filtered_rutas
from .models import MaintenancePlan, MaintenancePlanEntry


class AssetMaintenancePlanView(LoginRequiredMixin, generic.DetailView):
    model = Asset
    template_name = 'mto/asset_maintenance_plan.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset = self.get_object()
        user = self.request.user
        filtered_rutas, current_month_name_es = get_filtered_rutas(asset, self.request.GET)

        executing_rutas = []
        normal_rutas = []
        for r in filtered_rutas:
            if r.ot and r.ot.state == 'x':
                executing_rutas.append(r)
            else:
                normal_rutas.append(r)

        context['rotativos'] = Equipo.objects.filter(system__in=get_full_systems_ids(asset, user), tipo='r').exists()
        context['view_type'] = 'rutas'
        context['asset'] = asset
        context['mes'] = current_month_name_es
        context['page_obj_rutas'] = normal_rutas
        context['exec_rutas'] = executing_rutas
        context['rutinas_filter_form'] = RutinaFilterForm(self.request.GET or None, asset=asset)
        context['rutinas_disponibles'] = Ruta.objects.filter(system__asset=asset)

        ubicaciones = set()
        for r in filtered_rutas:
            if r.equipo and r.equipo.ubicacion:
                ubicaciones.add(r.equipo.ubicacion)

            if r.equipo and r.equipo.ubicacion: # Asignar r.ubic_label = su ubicación o "(sin)"
                r.ubic_label = r.equipo.ubicacion
            else:
                r.ubic_label = "(sin)"
        context['ubicaciones_unicas'] = sorted(ubicaciones)
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
                # Si se filtra por mes, se toma la entrada de ese mes; de lo contrario se agregan todos
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


