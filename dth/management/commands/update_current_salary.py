from django.core.management.base import BaseCommand
from dth.models import NominaReport

class Command(BaseCommand):
    help = "Actualiza el campo current_salary en NominaReport copiando el salary del empleado asociado."

    def handle(self, *args, **options):
        reports = NominaReport.objects.select_related('nomina').all()
        updated_count = 0
        for report in reports:
            new_salary = report.nomina.salary
            if report.current_salary != new_salary:
                report.current_salary = new_salary
                report.save(update_fields=['current_salary'])
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f"Actualizado NominaReport id={report.id}: current_salary = {new_salary}"
                ))
        self.stdout.write(self.style.SUCCESS(f"Proceso finalizado. Se actualizaron {updated_count} registros."))
