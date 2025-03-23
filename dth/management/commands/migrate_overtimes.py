from django.core.management.base import BaseCommand
from dth.models import Overtime, OvertimeProject, Nomina
from django.contrib.auth.models import User
from got.models import Asset

class Command(BaseCommand):
    help = "Migración de registros Overtime a OvertimeProject y actualización de campos relacionados."

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando proceso de migración...")

        # Diccionario para guardar combinaciones únicas (fecha, justificacion, asset_id)
        overtime_groups = {}

        overtimes = Overtime.objects.all().order_by('fecha')
        
        for overtime in overtimes:
            # Clave única para identificar combinaciones
            key = (overtime.fecha, overtime.justificacion, overtime.asset_id)
            
            if key not in overtime_groups:
                # Crear nuevo OvertimeProject
                project = OvertimeProject.objects.create(
                    description=overtime.justificacion,
                    asset=overtime.asset,
                    reported_by=overtime.reportado_por,
                    report_date=overtime.fecha
                )
                overtime_groups[key] = project
                self.stdout.write(self.style.SUCCESS(f"Proyecto creado: {project.id} - Fecha: {overtime.fecha}, Asset: {overtime.asset}, Reportado por: {overtime.reportado_por}"))
            
            # Asociar Overtime con el proyecto creado o existente
            overtime.project = overtime_groups[key]

            # Actualizar campo worker según cédula
            nomina_record = Nomina.objects.filter(id_number=overtime.cedula).first()
            if nomina_record:
                overtime.worker = nomina_record
                self.stdout.write(self.style.SUCCESS(f"Worker asociado a {overtime.nombre_completo}: {nomina_record.name} {nomina_record.surname} (id: {nomina_record.id})"))
            else:
                self.stdout.write(self.style.WARNING(f"No se encontró registro en Nomina para cédula {overtime.cedula} (Registro Overtime ID: {overtime.id})"))

            # Actualizar el estado según approved
            original_state = overtime.state
            overtime.state = 'a' if overtime.approved else 'c'
            self.stdout.write(f"Estado actualizado: de {original_state} a {overtime.state} para el registro Overtime ID: {overtime.id}")

            overtime.save()

        self.stdout.write(self.style.SUCCESS("Proceso de migración finalizado correctamente."))
