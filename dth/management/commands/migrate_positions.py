from django.core.management.base import BaseCommand
from dth.models.payroll import Nomina
from dth.models.positions import Position
from django.db import transaction

class Command(BaseCommand):
    help = 'Migra los cargos existentes desde Nomina hacia la tabla Position'

    def handle(self, *args, **options):
        positions_created = 0
        employees_updated = 0
        existing_positions = {}

        nomina_records = Nomina.objects.all()

        for record in nomina_records:
            cargo_actual = record.position.strip().lower()

            if cargo_actual in existing_positions:
                position = existing_positions[cargo_actual]
            else:
                position, created = Position.objects.get_or_create(name=cargo_actual)
                if created:
                    self.stdout.write(f"Se encontró un nuevo cargo: '{cargo_actual}'")
                    crear = input(f"¿Deseas crear el cargo '{cargo_actual}'? [s/n]: ").strip().lower()
                    if crear == 's':
                        categoria = ''
                        while categoria not in ['o', 'a', 'm']:
                            categoria = input("Selecciona la categoría: Operativo (o), Administrativo (a), Mixto (m): ").strip().lower()
                        position.category = categoria
                        position.save()
                        positions_created += 1
                        self.stdout.write(self.style.SUCCESS(f"Cargo '{cargo_actual}' creado exitosamente."))
                    else:
                        position.delete()
                        self.stdout.write(self.style.WARNING(f"Cargo '{cargo_actual}' no creado."))
                        continue
                existing_positions[cargo_actual] = position

            # Corrección aquí 👇:
            record.position_id = position
            record.save()
            employees_updated += 1
            self.stdout.write(self.style.SUCCESS(
                f"Empleado '{record.name} {record.surname}' actualizado con cargo '{position.name}'."
            ))

        self.stdout.write(self.style.SUCCESS(
            f"Proceso terminado: {positions_created} cargos creados, {employees_updated} empleados actualizados."
        ))
