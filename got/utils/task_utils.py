# got/utils/task_utils.py
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Value
from django.db.models.functions import Concat
from datetime import datetime, date, timedelta

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


def filter_tasks_queryset(request, base_queryset=None):
    if base_queryset is None:
        queryset = Task.objects.filter(ot__isnull=False)
    else:
        queryset = base_queryset

    asset_id = request.GET.get('asset_id')  # Filtro por asset
    if asset_id:
        queryset = queryset.filter(ot__system__asset_id=asset_id)

    worker_id = request.GET.get('worker')  # Filtro por usuario (worker)
    if worker_id:
        queryset = queryset.filter(responsible_id=worker_id)

    # 1) Revisar si daily = 'today' o 'tomorrow'
    daily_mode = request.GET.get('daily', '')  # puede ser '' / 'today' / 'tomorrow'
    if daily_mode == 'today':
        # Forzar start_date y end_date a HOY
        today_str = date.today().strftime('%Y-%m-%d')
        start_date_str = today_str
        end_date_str = today_str
        # De manera que omitas los params del usuario
    elif daily_mode == 'tomorrow':
        # Forzar start_date y end_date a MAÑANA
        tomorrow = date.today() + timedelta(days=1)
        tomorrow_str = tomorrow.strftime('%Y-%m-%d')
        start_date_str = tomorrow_str
        end_date_str   = tomorrow_str
    else:
        # Si no hay daily_mode, tomamos lo que venga en GET (o filtramos pendientes)
        start_date_str = request.GET.get('start_date')
        end_date_str   = request.GET.get('end_date')

    if not (start_date_str and end_date_str):
        queryset = queryset
    else:
        try:
            d_start = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            d_end = datetime.strptime(end_date_str,   '%Y-%m-%d').date()

            queryset = queryset.annotate(
                calc_final_date=models.ExpressionWrapper(
                    models.F('start_date') + DayInterval(models.F('men_time')),
                    output_field=models.DateField()
                )
            ).filter(calc_final_date__gte=d_start, start_date__lte=d_end)

        except ValueError:
            queryset = queryset

    # 4) Filtrar por supervisores en grupo mto_members si mto_only=1
    mto_only = request.GET.get('mto_only', '')
    if mto_only == '1':
        # Lista de nombres completos (first + last) de mto_members:
        mto_users = (
            User.objects.filter(groups__name='mto_members')
            .annotate(full_name=Concat('first_name', Value(' '), 'last_name'))
            .values_list('full_name', flat=True)
        )
        queryset = queryset.filter(ot__supervisor__in=mto_users)

    current_user = request.user  # Filtro adicional según el grupo del usuario
    if current_user.groups.filter(name='serport_members').exists():
        queryset = queryset.filter(responsible=current_user)
    elif current_user.groups.filter(name='mto_members').exists():
        pass
    elif current_user.groups.filter(
        name__in=['maq_members', 'buzos_members']
    ).exists():
        queryset = queryset.filter(ot__system__asset__supervisor=current_user)
    else:
        queryset = queryset.none()
    return queryset


def filter_by_mto_supervisors(queryset):
    # Crea una lista de nombres completos (ej: "Carlos Perez")
    mto_users = (
        User.objects.filter(groups__name='mto_members').annotate(
            full_name=Concat('first_name', Value(' '), 'last_name')
        ).values_list('full_name', flat=True)
    )

    # Filtrar queryset
    return queryset.filter(ot__supervisor__in=mto_users)