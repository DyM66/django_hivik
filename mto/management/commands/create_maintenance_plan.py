# mto/management/commands/create_maintenance_plans_asset.py

import calendar
from datetime import date, timedelta
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from mto.models import MaintenancePlan, MaintenancePlanEntry
from got.models import Asset, Ruta

class Command(BaseCommand):
    help = 'Crea planes de mantenimiento para todas las rutinas asociadas a un asset (por abreviatura) en un periodo dado.'

    def add_arguments(self, parser):
        parser.add_argument('asset_abbr', type=str, help='Abreviatura del asset')
        parser.add_argument('--start', type=str, help='Fecha de inicio del periodo (YYYY-MM-DD)', default="2025-02-01")
        parser.add_argument('--end', type=str, help='Fecha de fin del periodo (YYYY-MM-DD)', default="2025-12-31")

    def handle(self, *args, **options):
        asset_abbr = options['asset_abbr']
        start_str = options['start']
        end_str = options['end']
        try:
            period_start = date.fromisoformat(start_str)
            period_end = date.fromisoformat(end_str)
        except ValueError:
            raise CommandError("Las fechas deben estar en formato YYYY-MM-DD")
        
        try:
            asset = Asset.objects.get(abbreviation=asset_abbr)
        except Asset.DoesNotExist:
            raise CommandError(f"No existe el asset con abreviatura '{asset_abbr}'")
        
        # Obtenemos todas las rutas asociadas a este asset (a través de sus sistemas)
        rutas = Ruta.objects.filter(system__asset=asset)
        if not rutas.exists():
            self.stdout.write(self.style.WARNING(f"No se encontraron rutinas para el asset {asset.name}"))
            return

        # Iterar por cada ruta para crear el plan
        for ruta in rutas:
            self.stdout.write(f"Procesando ruta: {ruta.name} (Control: {ruta.control}, Frecuencia: {ruta.frecuency})")
            
            # Creamos el plan de mantenimiento. El campo start_count_date se fija a la fecha de intervención
            # en el momento de crear el plan, y a partir de ahí se calcularán las ejecuciones.
            plan = MaintenancePlan.objects.create(
                ruta=ruta,
                start_count_date=ruta.intervention_date,
                period_start=period_start,
                period_end=period_end
            )

            execution_dates = []
            # Caso 1: Rutina con control 'd' (días)
            if ruta.control == 'd':
                freq = ruta.frecuency  # Frecuencia en días
                current_date = plan.start_count_date
                while current_date <= period_end:
                    if current_date >= period_start:
                        execution_dates.append(current_date)
                    current_date += timedelta(days=freq)
            # Caso 2: Rutina con control 'h' (horas)
            elif ruta.control == 'h':
                # La primera fecha planificada se obtiene de la propiedad next_date
                first_date = ruta.next_date
                # Validar el promedio: si prom_hours es menor que 2, usar 2.
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
                self.stdout.write(self.style.WARNING(f"Ruta '{ruta.name}' tiene control '{ruta.control}', que no está implementado."))
                continue

            # Agrupar las fechas planificadas por (año, mes)
            planned_by_month = {}
            for dt in execution_dates:
                key = (dt.year, dt.month)
                planned_by_month[key] = planned_by_month.get(key, 0) + 1

            # Crear las entradas del plan para cada mes del periodo
            current = period_start
            while current <= period_end:
                key = (current.year, current.month)
                planned = planned_by_month.get(key, 0)
                MaintenancePlanEntry.objects.create(
                    plan=plan,
                    month=current.month,
                    year=current.year,
                    planned_executions=planned,
                    actual_executions=0
                )
                # Avanzar al primer día del siguiente mes
                if current.month == 12:
                    current = date(current.year + 1, 1, 1)
                else:
                    current = date(current.year, current.month + 1, 1)

            self.stdout.write(self.style.SUCCESS(f"Plan (ID: {plan.id}) y entradas creadas para la ruta '{ruta.name}'"))
