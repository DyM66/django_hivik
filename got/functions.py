from django.template.loader import get_template
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from io import BytesIO
from xhtml2pdf import pisa
from django.http import HttpResponse
from got.models import *
from collections import defaultdict
from datetime import date
import openpyxl
import pandas as pd


def actualizar_rutas_dependientes(ruta):
    ruta.intervention_date = timezone.now()
    ruta.save()
    if ruta.dependencia is not None:
        actualizar_rutas_dependientes(ruta.dependencia)


def generate_pdf_content(ot):

    template_path = 'got/pdf_template.html'
    context = {'ot': ot}
    template = get_template(template_path)
    html = template.render(context)
    pdf_content = BytesIO()

    pisa.CreatePDF(html, dest=pdf_content)

    return pdf_content.getvalue()


def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None


def copiar_rutas_de_sistema(system_id):
    sistema_origen = get_object_or_404(System, id=system_id)
    asset = sistema_origen.asset
    sistemas_destino = System.objects.filter(asset=asset).exclude(id=system_id)
    
    with transaction.atomic():
        for sistema in sistemas_destino:
            for ruta in sistema_origen.rutas.all():
                ruta_nueva = Ruta.objects.create(
                    name=ruta.name,
                    control=ruta.control,
                    frecuency=ruta.frecuency,
                    intervention_date=ruta.intervention_date,
                    astillero=ruta.astillero,
                    system=sistema,
                    # equipo=ruta.equipo.code,
                    dependencia=ruta.dependencia,
                )
                
                for tarea in ruta.task_set.all():
                    Task.objects.create(
                        ot=tarea.ot,
                        ruta=ruta_nueva,
                        responsible=tarea.responsible,
                        description=tarea.description,
                        procedimiento=tarea.procedimiento,
                        hse=tarea.hse,
                        news=tarea.news,
                        evidence=tarea.evidence,
                        start_date=tarea.start_date,
                        men_time=tarea.men_time,
                        finished=tarea.finished
                    )
    print(f"Rutas y tareas copiadas exitosamente a otros sistemas en el mismo activo {asset.name}.")

from datetime import datetime, timedelta
def calcular_repeticiones(ruta, periodo='anual'):
    periodos = {
        'trimestral': 90,
        'semestral': 180,
        'anual': 365,
        'quinquenal': 1825,  # 5 años
    }

    dias_periodo = periodos.get(periodo, 0)
    today = datetime.now().date()
    if ruta.control == 'd':
        frecuencia_dias = ruta.frecuency
        next_date = ruta.next_date

        repeticiones = 0
        if next_date and next_date <= today + timedelta(days=dias_periodo):
            repeticiones += 1
            # Calcular cuántas veces más ocurrirá la rutina dentro del periodo
            remaining_days = (today + timedelta(days=dias_periodo) - next_date).days
            repeticiones += remaining_days // frecuencia_dias
    
    elif ruta.get_control_display() == 'Horas':
        diferencia_dias = (ruta.next_date - ruta.intervention_date).days
        repeticiones = 0

        if diferencia_dias > 0:
            # Calcular la primera repetición
            next_date = ruta.next_date
            if next_date and next_date <= (today + timedelta(days=dias_periodo)):
                repeticiones += 1
                remaining_days = (today + timedelta(days=dias_periodo) - next_date).days
                repeticiones += remaining_days // diferencia_dias
    
    return repeticiones



def calcular_repeticiones2(ruta, periodo='anual'):
    periodos = {
        'trimestral': 90,
        'semestral': 180,
        'anual': 365,
        'quinquenal': 1825,  # 5 años
    }

    dias_periodo = periodos.get(periodo, 0)
    today = datetime.now().date()
    meses_ejecucion = []
    
    if ruta.control == 'd':
        frecuencia_dias = ruta.frecuency
        next_date = ruta.next_date

        repeticiones = 0
        if next_date and next_date <= today + timedelta(days=dias_periodo):
            repeticiones += 1
            meses_ejecucion.append(next_date.strftime('%B %Y'))
            remaining_days = (today + timedelta(days=dias_periodo) - next_date).days
            for _ in range(remaining_days // frecuencia_dias):
                next_date += timedelta(days=frecuencia_dias)
                meses_ejecucion.append(next_date.strftime('%B %Y'))
            repeticiones += remaining_days // frecuencia_dias
    
    elif ruta.get_control_display() == 'Horas':
        diferencia_dias = (ruta.next_date - ruta.intervention_date).days
        repeticiones = 0

        if diferencia_dias > 0:
            next_date = ruta.next_date
            if next_date and next_date <= (today + timedelta(days=dias_periodo)):
                repeticiones += 1
                meses_ejecucion.append(next_date.strftime('%B %Y'))
                remaining_days = (today + timedelta(days=dias_periodo) - next_date).days
                for _ in range(remaining_days // diferencia_dias):
                    next_date += timedelta(days=diferencia_dias)
                    meses_ejecucion.append(next_date.strftime('%B %Y'))
                repeticiones += remaining_days // diferencia_dias

    return repeticiones, meses_ejecucion


def consumibles_summary(asset):

    '''
    Función utilizada para calcular la cantidad de articulos de tipo consumible que se repiten dentro de un mismo
    Asset y asociarlo a un grupo Subsystem o General.
    '''

    equipos = Equipo.objects.filter(system__asset=asset).prefetch_related('suministros__item')
    item_subsystems = defaultdict(set)
    items_by_subsystem = defaultdict(set)
    item_cant = defaultdict(set)

    inventory_counts = defaultdict(int)
    suministros = Suministro.objects.filter(asset=asset)

    for suministro in suministros:
        inventory_counts[suministro.item] += suministro.cantidad

    for equipo in equipos:
        subsystem = equipo.subsystem if equipo.subsystem else "General"
        for suministro in equipo.suministros.all():
                item_subsystems[suministro.item].add(subsystem)
                if suministro.item in item_cant:
                    item_cant[suministro.item] += suministro.cantidad
                else:
                    item_cant[suministro.item] = suministro.cantidad
    
    duplicated_items = {item for item, subsystems in item_subsystems.items() if len(subsystems) > 1}

    for equipo in equipos:
        subsystem = equipo.subsystem if equipo.subsystem else "General"
        for suministro in equipo.suministros.all():
            item_tuple = (suministro.item, item_cant[suministro.item], inventory_counts[suministro.item], item_cant[suministro.item] * 2)
            if suministro.item in duplicated_items:
                items_by_subsystem["General"].add(item_tuple)
            else:
                items_by_subsystem[subsystem].add(item_tuple)
    
    items_by_subsystem = {k: list(v) for k, v in items_by_subsystem.items() if v}

    return items_by_subsystem


def buzos_station_filter(user):

    location_filters = {
        'santamarta_station': 'Santa Marta',
        'ctg_station': 'Cartagena',
        'guyana_station': 'Guyana',
    }
    
    locations = [loc for group, loc in location_filters.items() if user.groups.filter(name=group).exists()]
    if locations:
        return locations
    pass


def traductor(word):
    context = {
        "January": "Enero",
        "February": "Febrero",
        "March": "Marzo",
        "April": "Abril",
        "May": "Mayo",
        "June": "Junio",
        "July": "Julio",
        "August": "Agosto",
        "September": "Septiembre",
        "October": "Octubre",
        "November": "Noviembre",
        "December": "Diciembre"
    }
    return context[word]


def truncate_text(text, length=45):
    if len(text) > length:
        return text[:length] + '...'
    return text


def calculate_status_code(t):
    ot_tasks = Task.objects.filter(ot=t)

    earliest_start_date = min(t.start_date for t in ot_tasks)
    latest_final_date = max(t.final_date for t in ot_tasks)

    today = date.today()

    if latest_final_date < today:
        return 0
    elif earliest_start_date < today < latest_final_date:
        return 1
    elif earliest_start_date > today:
        return 2

    return None



def export_rutinas_to_excel(systems, filename="rutinas.xlsx"):
    data = []

    for system in systems:
        filtered_rutas = Ruta.objects.filter(system=system).exclude(system__state__in=['x', 's']).order_by('-nivel', 'frecuency')

        for ruta in filtered_rutas:
            days_left = (ruta.next_date - datetime.now().date()).days if ruta.next_date else '---'
            data.append({
                'asset': ruta.system.asset.name,  # Añadir el nombre del Asset
                'equipo_name': ruta.equipo.name if ruta.equipo else ruta.system.name,
                'location': ruta.equipo.system.location if ruta.equipo else ruta.system.location,
                'name': ruta.name,
                'frecuency': ruta.frecuency,
                'control': ruta.get_control_display(),
                'daysleft': days_left,
                'intervention_date': ruta.intervention_date.strftime('%d/%m/%Y') if ruta.intervention_date else '---',
                'next_date': ruta.next_date.strftime('%d/%m/%Y') if ruta.next_date else '---',
                'ot_num_ot': ruta.ot.num_ot if ruta.ot else '---',
                'activity': '---',  # Placeholder para la fila de la rutina en la columna de actividades
                'responsable': ''  # Columna vacía para la fila de la rutina
            })

            tasks = Task.objects.filter(ruta=ruta)
            for task in tasks:
                responsable_name = task.responsible.get_full_name() if task.responsible else '---'
                data.append({
                    'asset': ruta.system.asset.name,  # Mantener el nombre del Asset para las tareas
                    'equipo_name': '',
                    'location': '',
                    'name': '',
                    'frecuency': '',
                    'control': '',
                    'daysleft': '',
                    'intervention_date': '',
                    'next_date': '',
                    'ot_num_ot': '',
                    'activity': f'- {task.description}',
                    'responsable': responsable_name
                })

    # Convertimos la lista de diccionarios en un DataFrame
    df = pd.DataFrame(data)
    df.columns = ['Asset', 'Equipo', 'Ubicación', 'Código', 'Frecuencia', 'Control', 'Tiempo Restante', 'Última Intervención', 'Próxima Intervención', 'Orden de Trabajo', 'Actividad', 'Responsable']

    # Generamos la respuesta HTTP con el archivo Excel
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)

    return response


def update_equipo_code(old_code):

    equipo = Equipo.objects.get(code=old_code)
    system = equipo.system
    asset_abbreviation = system.asset.abbreviation
    group_number = system.group
    tipo = equipo.tipo.upper()

    similar_equipments = Equipo.objects.filter(
        code__startswith=f"{asset_abbreviation}-{group_number}-{tipo}"
    )
    sequence_number = similar_equipments.count() + 1
    sequence_str = str(sequence_number).zfill(3) 
    generated_code = f"{asset_abbreviation}-{group_number}-{tipo}-{sequence_str}"

    try:
        # Iniciar una transacción para asegurar que todo se actualice correctamente
        with transaction.atomic():
            # Obtener el equipo cuyo código se va a cambiar
            equipo = Equipo.objects.get(code=old_code)
            equipo.code = generated_code
            equipo.save()


            # Actualizar todas las relaciones donde esté relacionado el equipo
            print(f"Actualizando código de equipo de '{old_code}' a '{generated_code}'...")

            # HistoryHour
            updated_history_hours = HistoryHour.objects.filter(component__code=old_code).update(component=equipo)
            print(f"HistoryHour actualizado: {updated_history_hours} registros")

            # Suministro
            updated_suministros = Suministro.objects.filter(equipo__code=old_code).update(equipo=equipo)
            print(f"Suministro actualizado: {updated_suministros} registros")

            # Ruta
            updated_rutas = Ruta.objects.filter(equipo__code=old_code).update(equipo=equipo)
            print(f"Ruta actualizado: {updated_rutas} registros")

            # DailyFuelConsumption
            updated_daily_fuel = DailyFuelConsumption.objects.filter(equipo__code=old_code).update(equipo=equipo)
            print(f"DailyFuelConsumption actualizado: {updated_daily_fuel} registros")

            # FailureReport
            updated_failure_reports = FailureReport.objects.filter(equipo__code=old_code).update(equipo=equipo)
            print(f"FailureReport actualizado: {updated_failure_reports} registros")

            # Megger
            updated_megger = Megger.objects.filter(equipo__code=old_code).update(equipo=equipo)
            print(f"Megger actualizado: {updated_megger} registros")

            # Preoperacional
            updated_preoperacional = Preoperacional.objects.filter(vehiculo__code=old_code).update(vehiculo=equipo)
            print(f"Preoperacional actualizado: {updated_preoperacional} registros")

            # PreoperacionalDiario
            updated_preoperacional_diario = PreoperacionalDiario.objects.filter(vehiculo__code=old_code).update(vehiculo=equipo)
            print(f"PreoperacionalDiario actualizado: {updated_preoperacional_diario} registros")

            # Transferencia
            updated_transferencia_origen = Transferencia.objects.filter(origen__equipos__code=old_code).update(origen=equipo.system)
            updated_transferencia_destino = Transferencia.objects.filter(destino__equipos__code=old_code).update(destino=equipo.system)
            print(f"Transferencia actualizado: {updated_transferencia_origen + updated_transferencia_destino} registros")

            # DarBaja
            updated_darbaja = DarBaja.objects.filter(equipo__code=old_code).update(equipo=equipo)
            print(f"DarBaja actualizado: {updated_darbaja} registros")

            # Image
            updated_images = Image.objects.filter(equipo__code=old_code).update(equipo=equipo)
            print(f"Image actualizado: {updated_images} registros")

            # Document
            updated_documents = Document.objects.filter(equipo__code=old_code).update(equipo=equipo)
            print(f"Document actualizado: {updated_documents} registros")

            print(f"El código del equipo '{old_code}' ha sido actualizado a '{generated_code}' en todas las tablas relacionadas.")
    
    except Equipo.DoesNotExist:
        print(f"El equipo con código '{old_code}' no existe.")
    except Exception as e:
        print(f"Ha ocurrido un error: {str(e)}")

