import holidays
from datetime import timedelta, datetime, time, date
from dateutil.relativedelta import relativedelta

# Horarios de trabajo
WEEKDAY_START = time(7, 30)
WEEKDAY_END = time(17, 0)
SATURDAY_START = time(8, 0)
SATURDAY_END = time(12, 0)
DAY_START = time(6, 0)   # 6:00 AM
NIGHT_START = time(21, 0)  # 9:00 PM

COLOMBIA_HOLIDAYS = holidays.Colombia(years=[2025, 2026, 2027, 2028])

def calculate_overtime(fecha, hora_inicio, hora_fin):
    overtime_periods = []
    day_type = None  # 'weekday', 'saturday', 'sunday', 'holiday'

    if fecha in COLOMBIA_HOLIDAYS:
        day_type = 'holiday'
    elif fecha.weekday() == 6:  # Domingo
        day_type = 'sunday'
    elif fecha.weekday() == 5:  # Sábado
        day_type = 'saturday'
    else:
        day_type = 'weekday'

    # Definir el horario laboral según el tipo de día
    if day_type == 'weekday':
        start_work = WEEKDAY_START
        end_work = WEEKDAY_END
    elif day_type == 'saturday':
        start_work = SATURDAY_START
        end_work = SATURDAY_END
    else:
        # Domingos y festivos: todo es horas extras
        if hora_inicio < hora_fin:
            overtime_periods.append((hora_inicio, hora_fin))
        return overtime_periods

    # Horas antes del inicio de la jornada laboral
    if hora_inicio < start_work:
        overtime_periods.append((hora_inicio, min(hora_fin, start_work)))

    # Horas después del fin de la jornada laboral
    if hora_fin > end_work:
        overtime_periods.append((max(hora_inicio, end_work), hora_fin))

    # Horas completamente fuera del horario laboral
    if hora_inicio >= hora_fin:
        return overtime_periods

    if hora_inicio >= end_work or hora_fin <= start_work:
        overtime_periods.append((hora_inicio, hora_fin))
    return overtime_periods


def subtract_time_ranges(new_start, new_end, existing_ranges):
    if new_start >= new_end:
        return []

    # Empezamos con la lista "result" con un solo intervalo (new_start, new_end)
    result = [(new_start, new_end)]

    for (ex_start, ex_end) in existing_ranges:
        tmp = []
        for (cur_start, cur_end) in result:
            # Si no hay solapamiento, lo dejamos igual
            if ex_end <= cur_start or ex_start >= cur_end:
                # [ex_start,ex_end] está totalmente fuera de [cur_start,cur_end]
                tmp.append((cur_start, cur_end))
            else:
                # Se solapan => dividir
                # Parte izquierda (si existe)
                if ex_start > cur_start:
                    tmp.append((cur_start, ex_start))
                # Parte derecha (si existe)
                if ex_end < cur_end:
                    tmp.append((ex_end, cur_end))
        result = tmp
        if not result:
            # Ya no queda nada, podemos cortar
            break
    return result


def hours_to_hhmm(total_hours):
    """Convierte total_hours (float) en un string 'X horas y Y minutos'."""
    hours = int(total_hours)
    minutes = int(round((total_hours - hours) * 60))
    return f"{hours}:{minutes}"


def is_sunday_or_holiday(date_):
    """Devuelve True si la fecha es domingo o festivo en Colombia."""
    if date_.weekday() == 6:  # domingo => weekday() == 6
        return True
    return date_ in COLOMBIA_HOLIDAYS


def diff_in_hours(tstart, tend):
    """
    Calcula la diferencia en horas (float) entre tstart y tend,
    asumiendo que están el mismo día y tend >= tstart.
    Si tend < tstart, se asume que cruza medianoche y se suma 1 día.
    """
    dt1 = datetime.combine(datetime.min.date(), tstart)
    dt2 = datetime.combine(datetime.min.date(), tend)
    if dt2 < dt1:
        # caso: end es "después de medianoche"
        dt2 += timedelta(days=1)
    diff = (dt2 - dt1).total_seconds() / 3600
    return diff



def overlap_in_hours(start, end, range_start, range_end):
    """
    Devuelve la cantidad de horas que el intervalo [start,end] 
    solapa con [range_start, range_end] (en el mismo día).
    """
    # Convertimos a datetime min
    dt_start = datetime.combine(datetime.min.date(), start)
    dt_end = datetime.combine(datetime.min.date(), end)
    dt_rstart = datetime.combine(datetime.min.date(), range_start)
    dt_rend = datetime.combine(datetime.min.date(), range_end)

    # Ajuste si dt_end < dt_start => +1 día
    if dt_end < dt_start:
        dt_end += timedelta(days=1)

    # Hallar la intersección
    latest_start = max(dt_start, dt_rstart)
    earliest_end = min(dt_end, dt_rend)
    if earliest_end > latest_start:
        return (earliest_end - latest_start).total_seconds() / 3600
    else:
        return 0


def get_default_date_range():
    today = date.today()
    if today.day < 21:
        start_date = (today - relativedelta(months=1)).replace(day=21)
        end_date = today.replace(day=21)
    else:
        start_date = today.replace(day=21)
        end_date = (today + relativedelta(months=1)).replace(day=21)
    return start_date, end_date


def parse_date_range(request):
    date_range_str = request.GET.get('date_range', '')
    if date_range_str:
        # Detecta separadores posibles
        if " to " in date_range_str:
            dates = date_range_str.split(" to ")
        elif " a " in date_range_str:
            dates = date_range_str.split(" a ")
        elif "," in date_range_str:
            dates = date_range_str.split(",")
        else:
            dates = []
        if len(dates) == 2:
            try:
                start_date = datetime.strptime(dates[0].strip(), '%Y-%m-%d').date()
                end_date = datetime.strptime(dates[1].strip(), '%Y-%m-%d').date()
            except ValueError:
                start_date, end_date = get_default_date_range()
        else:
            try:
                start_date = datetime.strptime(date_range_str.strip(), '%Y-%m-%d').date()
                end_date = start_date + timedelta(days=1)
            except ValueError:
                start_date, end_date = get_default_date_range()
    else:
        start_date, end_date = get_default_date_range()
    return start_date, end_date