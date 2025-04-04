from django import template
from got.models import Asset, FailureReport, Equipo
from inv.models import Solicitud
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from dth.models import UserProfile
import os
from django.db.models.functions import Concat
from django.db.models import Value
from decimal import Decimal
from datetime import datetime

register = template.Library()


@register.filter
def filter_by_date_range(images, date_range):
    """
    Filtra las imágenes por su fecha de creación (campo 'creation'),
    según 'date_range' en formato:
      - ""
      - "YYYY-MM-DD"
      - "YYYY-MM-DD,YYYY-MM-DD"
    Si no hay rango o falla el parse, retornamos sin filtrar.
    """
    if not date_range:
        # no hay rango => retorna todas
        return images

    try:
        # date_range podría ser "YYYY-MM-DD" o "YYYY-MM-DD,YYYY-MM-DD"
        if ',' in date_range:
            start_str, end_str = date_range.split(',', 1)
        else:
            start_str = date_range
            end_str = date_range

        start_str = start_str.strip()
        end_str   = end_str.strip()
        if not start_str:
            return images

        if not end_str:
            end_str = start_str

        start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
        end_date   = datetime.strptime(end_str,   "%Y-%m-%d").date()

        return images.filter(
            creation__gte=start_date,
            creation__lte=end_date
        )
    except ValueError:
        # Si algo falla en el parseo, no filtramos
        return images


@register.filter
def currency(value):
    try:
        val = Decimal(value)
    except:
        val = Decimal('0.00')
    # Formatear con separador de miles y 2 decimales
    return f"COP {val:,.2f}"

@register.filter(name='endswith')
def endswith(value, arg):
    """
    Devuelve True si el valor termina con el argumento proporcionado.
    """
    return value.endswith(arg)

@register.filter(name='basename')
def basename(value):
    """
    Devuelve el nombre base de una ruta de archivo.
    """
    return os.path.basename(value)


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

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def dict_get(d, key):
    return d.get(key, "")

@register.filter(name='range')
def custom_range(value):
    return range(value)

@register.filter(name='asset_info')
def return_asset(id):
    if not id:
        return ''
    try:
        return Asset.objects.get(abbreviation=id)
    except Asset.DoesNotExist:
        return '' 

@register.filter(name='user_info')
def return_name(id):
    if not id:
        return ''  # Si no se pasa un ID o es vacío, devuelve una cadena vacía
    try:
        u = User.objects.get(id=id)
        return u.get_full_name()
    except User.DoesNotExist:
        return ''
    

@register.filter(name='counter')
def counter(value):
    return value.count()


@register.filter(name='get_cargo')
def get_cargo(full_name):
    try:
        user = User.objects.annotate(
            full_name=Concat('first_name', Value(' '), 'last_name')
        ).get(full_name__iexact=full_name)
        return user.profile.cargo
    except (User.DoesNotExist, UserProfile.DoesNotExist):
        return ''
    
@register.filter
def get_firma(full_name):
    """
    Dada una cadena con el nombre completo (nombre y apellido),
    retorna la URL de la firma del usuario si existe y tiene un UserProfile asociado.
    """
    try:
        first_name, last_name = full_name.strip().split(' ', 1)
        user = User.objects.get(first_name__iexact=first_name, last_name__iexact=last_name)
        if hasattr(user, 'profile') and user.profile.firma:
            return user.profile.firma.url
        else:
            return ''
    except (User.DoesNotExist, ValueError):
        return ''
    

@register.filter
def dict_key(d, key):
    return d.get(key, None)

@register.simple_tag
def obtener_vehiculos():
    return Equipo.objects.filter(system__asset__abbreviation='VEH').order_by('name')



@register.filter
def index(sequence, position):
    """
    Retorna sequence[position].
    sequence puede ser una lista o tupla
    position se convierte a int (o lanza error si no es convertible).
    """
    try:
        pos = int(position)
        return sequence[pos]
    except:
        return None
    
@register.filter
def enumerate(value):
    return list(enumerate(value))

@register.filter
def replace_comma(value):
    """
    Reemplaza comas por puntos en una cadena.
    """
    try:
        return str(value).replace(',', '.')
    except:
        return value
    


@register.filter
def filter_ot_state(asset, state_value):
    return asset.ot_set.filter(state=state_value)



@register.filter
def filter_queryset(queryset, args):
    """
    Filtra un queryset según un argumento en formato "clave=valor".
    Ejemplo de uso:
        {% with tasks=ot.task_set|filter_queryset:"finished=False" %}
    """
    try:
        key, value = args.split('=')
        key = key.strip()
        value = value.strip()
        # Convertir el valor a booleano si es 'true' o 'false'
        if value.lower() == 'true':
            value = True
        elif value.lower() == 'false':
            value = False
        return queryset.filter(**{key: value})
    except Exception:
        return queryset
    


@register.filter
def first_line(value):
    """
    Devuelve sólo la primera línea del texto.
    """
    if not value:
        return ""
    return value.splitlines()[0]

