# got/utils/task_utils.py
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Value
from django.db.models.functions import Concat
from datetime import datetime

from datetime import datetime
from got.models import Task


def operational_users():
    valid_groups = [
        "serport_members", "mto_members", "buzos_members", "maq_members"
    ]
    all_users = (
        User.objects.filter(
            is_active=True, groups__name__in=valid_groups
        ).distinct().order_by('first_name', 'last_name')
    )
    return all_users


class DayInterval(models.Func):
    """
    Convierte un valor entero (por ejemplo men_time) en un intervalo de días
    para PostgreSQL. Permite hacer: start_date + DayInterval(F('men_time')).
    """
    function = ''  # No utilizamos una función nativa, sino un template
    template = '(%(expressions)s) * INTERVAL \'1 day\''
    output_field = models.DurationField()


def filter_tasks_queryset(request):
    queryset = Task.objects.filter(ot__isnull=False)

    estado_param = request.GET.get('estado', '')
    if estado_param not in ['0', '1', '2']:
        # Si no viene nada o viene algo inválido, por defecto mostramos solo pendientes
        estado_param = '0'

    if estado_param == '0':
        queryset = queryset.filter(finished=False)
    elif estado_param == '1':
        # no filtramos nada por finished
        pass
    else:  # estado_param == '2'
        queryset = queryset.filter(finished=True)

    user = request.user
    if user.groups.filter(name='serport_members').exists():
        queryset = queryset.filter(responsible=user)
    elif user.groups.filter(name='mto_members').exists():
        pass
    elif user.groups.filter(name__in=['maq_members', 'buzos_members']).exists():
        queryset = queryset.filter(ot__system__asset__supervisor=user)
    else:
        return queryset.none()
    
    show_mto = request.GET.get('show_mto_supervisors', '')
    if user.groups.filter(name='mto_members').exists():
        if show_mto == '1':
            mto_supervisors = (
                User.objects.filter(groups__name='mto_members')
                .annotate(full_name=Concat('first_name', Value(' '), 'last_name'))
                .values_list('full_name', flat=True)
            )
            queryset = queryset.filter(ot__supervisor__in=mto_supervisors)


    asset_id = request.GET.get('asset_id')  # Filtro por asset
    if asset_id:
        queryset = queryset.filter(ot__system__asset_id=asset_id)

    worker_id = request.GET.get('worker')  # Filtro por usuario (worker)
    if worker_id:
        queryset = queryset.filter(responsible_id=worker_id)

    start_date_str = request.GET.get('start_date')
    end_date_str   = request.GET.get('end_date')
    d_start, d_end = None, None
    if start_date_str and end_date_str:
        try:
            d_start = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            d_end   = datetime.strptime(end_date_str,   '%Y-%m-%d').date()
        except ValueError:
            pass

    if d_start and d_end:
        queryset = queryset.annotate(
            calc_final_date=models.ExpressionWrapper(
                models.F('start_date') + DayInterval(models.F('men_time')),
                output_field=models.DateField()
            )
        ).filter(
            calc_final_date__gte=d_start,
            start_date__lte=d_end
        )

    return queryset.order_by('ot__system__asset__name', 'start_date', 'ot__num_ot', 'priority')
