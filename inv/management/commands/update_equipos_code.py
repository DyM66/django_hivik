# inv/management/commands/update_equipos_code.py

from django.core.management.base import BaseCommand
from got.models import Equipo
from got.utils import update_equipo_code

class Command(BaseCommand):
    help = 'Actualiza los códigos de todos los equipos a la nueva estandarización.'

    def handle(self, *args, **options):
        equipos = Equipo.objects.all()
        total = equipos.count()
        self.stdout.write(f"Actualizando códigos de {total} equipos...")

        for idx, equipo in enumerate(equipos, start=1):
            old_code = equipo.code
            update_equipo_code(old_code)
            if idx % 100 == 0:
                self.stdout.write(f"Procesados {idx}/{total} equipos.")

        self.stdout.write(self.style.SUCCESS('Actualización de códigos completada.'))
