from django.template.loader import get_template
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from io import BytesIO
from xhtml2pdf import pisa
from django.http import HttpResponse

from got.models import System, Ruta, Task

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


from datetime import timedelta

def calcular_repeticiones(ruta, periodo):
    # Definir los días que representa cada periodo
    periodos = {
        'trimestral': 90,
        'semestral': 180,
        'anual': 365,
        'quinquenal': 1825,  # 5 años
    }

    dias_periodo = periodos.get(periodo, 0)

    if ruta.get_control_display() == 'Dias':
        # Si la rutina es en días, calcular cuántas veces se repetirá en el periodo
        frecuencia_dias = ruta.frecuency
        repeticiones = dias_periodo // frecuencia_dias
    
    elif ruta.get_control_display() == 'Horas':
        # Si la rutina es en horas, calcular la diferencia en días y luego las repeticiones
        diferencia_dias = (ruta.next_date - ruta.intervention_date).days
        if diferencia_dias > 0:
            repeticiones = dias_periodo // diferencia_dias
        else:
            repeticiones = 0  # Si la diferencia es negativa o cero, no se repite
    
    return repeticiones
