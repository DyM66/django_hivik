# myapp/management/commands/reformat_field.py

import sys
from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from django.db import transaction

VALID_FORMATS = ['upper', 'lower', 'capital', 'title']

def apply_format(value, fmt):
    """Aplica el formateo deseado a un string."""
    if fmt == 'upper':
        return value.upper()
    elif fmt == 'lower':
        return value.lower()
    elif fmt == 'capital':  # Primera letra mayúscula, resto minúscula
        return value.capitalize()  # "hola mundo" -> "Hola mundo"
    elif fmt == 'title':    # Primera letra de cada palabra
        return value.title() # "hola mundo" -> "Hola Mundo"
    else:
        return value

class Command(BaseCommand):
    """
    Comando para reescribir el contenido de un campo string en un modelo
    según un formato (upper, lower, capital, title).
    Si detecta que varios valores distintos se convertirían en uno igual
    (colisión), preguntará interactivamente cómo resolverlo.
    """
    help = "Reformatea un campo de texto de un modelo (upper, lower, capital, title), preguntando por colisiones."

    def add_arguments(self, parser):
        # Argumentos obligatorios
        parser.add_argument('app_label_dot_model', type=str,
                            help="Modelo en formato app_label.ModelName")
        parser.add_argument('field_name', type=str,
                            help="Nombre del campo de texto a reformatear")
        parser.add_argument('format', choices=VALID_FORMATS,
                            help="Tipo de formateo: upper, lower, capital o title")

    def handle(self, *args, **options):
        app_model = options['app_label_dot_model']
        field_name = options['field_name']
        fmt = options['format']

        try:
            app_label, model_name = app_model.split('.')
        except ValueError:
            raise CommandError("Usa el formato app_label.ModelName, por ejemplo 'dth.Nomina'")

        # Obtener el Modelo
        try:
            Model = apps.get_model(app_label, model_name)
        except LookupError:
            raise CommandError(f"No se encontró el modelo '{app_label}.{model_name}'")

        # Verificar si el campo existe
        if not hasattr(Model, field_name):
            raise CommandError(f"El modelo {Model.__name__} no tiene un campo '{field_name}'")

        # 1) Tomamos todos los valores DISTINTOS de ese campo
        distinct_values = (Model.objects
                           .order_by()
                           .values_list(field_name, flat=True)
                           .distinct())
        distinct_values = [v for v in distinct_values if v is not None]  # ignorar los Null

        # 2) Vamos a mapear el valor_origen -> valor_formateado
        #    y detectar colisiones.
        mapping = {}           # "Capitan" -> "CAPITAN"
        inverse_map = {}       # "CAPITAN" -> lista de ["Capitan","CAPITAN","capitan", ...]
        
        for original_val in distinct_values:
            new_val = apply_format(original_val, fmt)

            if new_val not in inverse_map:
                inverse_map[new_val] = [original_val]
                mapping[original_val] = new_val
            else:
                # colisión: ya existe un new_val con otra(s) old_val(s)
                # Por ejemplo, "Capitan" y "CAPITAN" -> "CAPITAN"
                collision_list = inverse_map[new_val]

                # Si original_val no está en la lista, lo agregamos
                if original_val not in collision_list:
                    collision_list.append(original_val)

        # 3) Si no hay colisiones (i.e. cada new_val corresponde a una sola old_val),
        #    no necesitamos interactuar. Pero si hay colisiones, preguntamos.
        #    "Colisión" aquí = un new_val con 2+ old_val distintos.
        for new_val, old_vals in inverse_map.items():
            if len(old_vals) > 1:
                self.stdout.write(self.style.WARNING(
                    f"\nSe ha detectado colisión: {old_vals} -> '{new_val}'"
                ))
                for val in old_vals:
                    self.stdout.write(f"  - Valor antiguo: '{val}' formateado => '{new_val}'")
                
                self.stdout.write("Debes indicar cómo quieres renombrar cada valor en conflicto.")
                # Para cada old_val, pedimos al usuario un new_val distinto:
                for val in old_vals:
                    # Mostramos un prompt
                    while True:
                        # Ejemplo: "El valor 'Capitan' se colisiona a 'CAPITAN'. ¿Cómo deseas escribirlo?"
                        msg = (f"El valor '{val}' se convertiría en '{new_val}'.\n"
                               "Por favor, escribe la versión final que deseas (o Enter para omitir): ")
                        user_input = input(msg).strip()
                        if not user_input:
                            # si el usuario no escribe nada, mantenemos la colisión, 
                            # o le podemos volver a preguntar, a gusto
                            self.stdout.write("No puede quedar vacío. Intente nuevamente.")
                            continue
                        else:
                            # Reemplazamos en el mapping
                            mapping[val] = user_input
                            break

        # 4) Aplicamos los cambios en la BD
        self.stdout.write(self.style.NOTICE("\nAplicando los cambios en la base de datos..."))

        with transaction.atomic():
            # Recorremos registro por registro (puede ser costoso si la tabla es grande).
            # Alternativamente, podríamos hacer un update masivo si no necesitáramos
            # distinciones por valor. Pero aquí cada old_val puede tener un new_val distinto
            # tras las correcciones manuales.
            objs = Model.objects.all()
            count_updates = 0

            for obj in objs:
                current_val = getattr(obj, field_name)
                if current_val is None:
                    continue
                if current_val in mapping:
                    desired_val = mapping[current_val]
                    if desired_val != current_val:  # Sólo si efectivamente cambia
                        setattr(obj, field_name, desired_val)
                        obj.save(update_fields=[field_name])
                        count_updates += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n¡Listo! Se han actualizado {count_updates} registros en {Model.__name__}."
        ))
