from django import template
from got.models import Asset, FailureReport, Solicitud
from django.contrib.auth.models import Group
from simple_history.models import HistoricalRecords
from math import ceil


register = template.Library()


@register.simple_tag(takes_context=True)
def obtener_asset_del_supervisor(context):
    request = context['request']
    user = request.user
    target_groups = ['maq_members', 'serport_members']
    user_groups = user.groups.filter(name__in=target_groups).values_list('name', flat=True)

    if user_groups:
        try:
            return Asset.objects.get(supervisor=user)
        except Asset.DoesNotExist:
            return None
    return None
    # if user.groups.filter(name='maq_members').exists():
    #     try:
    #         return Asset.objects.get(supervisor=user)
    #     except Asset.DoesNotExist:
    #         pass
    # return False


@register.filter(name='has_group')
def has_group(user, group_name):
    group = Group.objects.get(name=group_name)
    return True if group in user.groups.all() else False


@register.filter(name='get_impact_display')
def get_impact_display(impact_code):
    return FailureReport().get_impact_display(impact_code)


@register.filter(name='can_edit_task')
def can_edit_task(user, task):
    return user == task.responsible or user.has_perm('myapp.can_modify_any_task')


@register.filter
def get_mapping_value(mapping, key):
    return mapping.get(key, None)


@register.filter(name='format_number')
def format_number(value):
    try:
        value = float(value)
    except ValueError:
        return value 
    except TypeError:
        return value 
    
    suffix = 'Ω'
    if value >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.2f}T{suffix}"
    elif value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}G{suffix}"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M{suffix}"
    elif value >= 1_000:
        return f"{value / 1_000:.2f}K{suffix}"
    else:
        return f"{value}{suffix}"
    

@register.simple_tag
def get_page(solicitud_id, paginate_by=20):
    try:
        solicitud = Solicitud.objects.get(id=solicitud_id)
        position = len(list(Solicitud.objects.order_by('id'))) - (list(Solicitud.objects.order_by('id')).index(solicitud) + 1) 
        page = (position // paginate_by) + 1
        # page = position
        return page
    except Solicitud.DoesNotExist:
        return None
    


@register.filter
def calcular_repeticiones(ruta, periodo):
    # Definir los días que representa cada periodo
    periodos = {
        'trimestral': 90,
        'semestral': 180,
        'anual': 365,
        'quinquenal': 1825,  # 5 años
    }

    dias_periodo = periodos.get(periodo, 0)

    if ruta.control == 'd':
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

@register.filter
def range_filter(value):
    return range(value)