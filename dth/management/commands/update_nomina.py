import openpyxl
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from dth.models import Nomina

class Command(BaseCommand):
    help = "Lee un archivo Excel y actualiza/crea registros en Nomina."

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Ruta del archivo Excel que contiene la información de nómina.',
            required=True
        )

    def handle(self, *args, **options):
        file_path = options['file']
        self.stdout.write(self.style.NOTICE(f"Leyendo archivo: {file_path}"))

        # Cargar el workbook y la hoja
        wb = openpyxl.load_workbook(file_path)
        ws = wb["Hoja1"]  # Ajusta el nombre de la hoja si difiere

        found_blank_row = False

        # Recorrer las filas (saltando la fila de cabecera)
        for row in ws.iter_rows(min_row=2, values_only=True):
            """
            Suponiendo que las columnas están en este orden:
            A: Codigo
            B: nombres
            C: apellidos
            D: Ingreso
            E: Vence
            F: Centro Costo (no lo guardamos en Nomina, pero podrías usarlo si deseas)
            G: Cargo
            H: SALARIO
            """
            # 1) Omitir fila si está completamente en blanco:
            if all(cell is None for cell in row):
                found_blank_row = True
                # Rompe el bucle y pasa a la siguiente lógica
                break

            (doc_number, name, surname, admission_str, expiration_str,
             cost_center, cargo, salary) = row

            # Convertir las fechas (si no están vacías)
            admission_date = None
            if admission_str:
                # Asumiendo que vienen en formato YYYY/MM/DD (e.g. "2025/01/09")
                admission_date = datetime.strptime(str(admission_str), "%Y/%m/%d").date()

            expiration_date = None
            if expiration_str:
                expiration_date = datetime.strptime(str(expiration_str), "%Y/%m/%d").date()

            # Buscar si existe un registro con ese doc_number
            try:
                nomina_obj = Nomina.objects.get(doc_number=doc_number)
                # Verificar qué campos difieren y actualizarlos
                changed = False

                if nomina_obj.name != name:
                    nomina_obj.name = name
                    changed = True

                if nomina_obj.surname != surname:
                    nomina_obj.surname = surname
                    changed = True

                if nomina_obj.admission != admission_date:
                    nomina_obj.admission = admission_date
                    changed = True

                if nomina_obj.expiration != expiration_date:
                    nomina_obj.expiration = expiration_date
                    changed = True

                if nomina_obj.position != cargo:
                    nomina_obj.position = cargo
                    changed = True

                # salary podría ser float o Decimal; ajusta según tu modelo
                if float(nomina_obj.salary) != float(salary):
                    nomina_obj.salary = salary
                    changed = True

                if changed:
                    nomina_obj.save()
                    self.stdout.write(self.style.SUCCESS(
                        f"Registro actualizado para {doc_number}"
                    ))
                else:
                    self.stdout.write(f"Sin cambios para {doc_number}")

            except Nomina.DoesNotExist:
                # Crear un nuevo registro si no existe
                Nomina.objects.create(
                    doc_number=doc_number,
                    name=name,
                    surname=surname,
                    admission=admission_date,
                    expiration=expiration_date,
                    position=cargo,
                    salary=salary
                )
                self.stdout.write(self.style.SUCCESS(
                    f"Registro creado para {doc_number}"
                ))

        if found_blank_row:
            self.stdout.write(self.style.WARNING("Se encontró una fila en blanco. El proceso se detuvo."))
        else:
            self.stdout.write(self.style.SUCCESS("Proceso finalizado exitosamente sin filas en blanco."))
