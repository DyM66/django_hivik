import openpyxl
from django.core.management.base import BaseCommand
from dth.models import Nomina

class Command(BaseCommand):
    help = "Lee un archivo Excel y actualiza el campo 'risk_class' en Nomina según el valor de la columna '%'."

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Ruta del archivo Excel que contiene la información de clase de riesgo.',
            required=True
        )

    def handle(self, *args, **options):
        file_path = options['file']
        self.stdout.write(self.style.NOTICE(f"Leyendo archivo: {file_path}"))

        # Ajustamos el diccionario con los valores redondeados a 3 decimales
        # (o los decimales que requieras).
        # 6.960 => 6.96, 0.522 => 0.522, etc.
        risk_mapping = {
            0.522: 'I',
            1.044: 'II',
            2.436: 'III',
            4.350: 'IV',
            6.960: 'V'
        }

        wb = openpyxl.load_workbook(file_path)
        ws = wb["Hoja1"]  # Ajusta el nombre de la hoja

        for row in ws.iter_rows(min_row=2, values_only=True):
            if all(cell is None for cell in row):
                self.stdout.write(self.style.WARNING(
                    "Se encontró una fila en blanco. Se detiene el proceso."
                ))
                break

            doc_number = row[0]
            name_in_excel = row[1]
            percentage_val = row[2]

            if not doc_number:
                self.stdout.write(self.style.WARNING(
                    "doc_number vacío. Se detiene el proceso."
                ))
                break

            if percentage_val is None:
                self.stdout.write(f"Omitiendo {doc_number}: no hay valor en '%'.")
                continue

            # Verificamos si es float o string
            try:
                if isinstance(percentage_val, float):
                    # p.ej. 0.0696 => 6.96
                    percentage_value = percentage_val * 100
                else:
                    # p.ej. "6.960%" => "6.960" => float => 6.96
                    percentage_value = float(percentage_val.replace('%', '').strip())

                # Redondeamos a 3 decimales
                val_rounded = round(percentage_value, 3)

            except ValueError:
                self.stdout.write(self.style.ERROR(
                    f"No se pudo convertir '{percentage_val}' a float. Fila con doc_number={doc_number}"
                ))
                continue

            # Ahora buscamos val_rounded en el diccionario
            if val_rounded not in risk_mapping:
                self.stdout.write(self.style.ERROR(
                    f"El valor {val_rounded} no está definido en el mapping para doc_number={doc_number}."
                ))
                continue

            new_risk_class = risk_mapping[val_rounded]

            # Buscar en Nomina
            try:
                nomina_obj = Nomina.objects.get(doc_number=str(doc_number))
            except Nomina.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f"No existe registro en Nomina con doc_number={doc_number}. Se omite."
                ))
                continue

            # Actualizar si difiere
            if nomina_obj.risk_class != new_risk_class:
                old_value = nomina_obj.risk_class
                nomina_obj.risk_class = new_risk_class
                nomina_obj.save()
                self.stdout.write(self.style.SUCCESS(
                    f"Actualizado doc_number={doc_number} de '{old_value}' a '{new_risk_class}'."
                ))
            else:
                self.stdout.write(
                    f"Sin cambios para doc_number={doc_number} (risk_class ya es '{new_risk_class}')."
                )

        self.stdout.write(self.style.SUCCESS("Proceso finalizado."))
