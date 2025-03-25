import holidays
from datetime import timedelta, datetime, time

# Horarios de trabajo
WEEKDAY_START = time(7, 30)
WEEKDAY_END = time(17, 0)
SATURDAY_START = time(8, 0)
SATURDAY_END = time(12, 0)

COLOMBIA_HOLIDAYS = holidays.Colombia()

def calcular_horas_extras(fecha, hora_inicio, hora_fin):
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

def overlap_interval(report_start, report_end, period_start, period_end):
    """
    Retorna el solapamiento (timedelta) entre el intervalo del reporte y el intervalo
    de período nocturno.
    """
    latest_start = max(report_start, period_start)
    earliest_end = min(report_end, period_end)
    delta = earliest_end - latest_start
    return max(delta, timedelta(0))


def get_nocturnal_overlap(dt_start, dt_end):
    """
    Calcula el total de tiempo (timedelta) del intervalo [dt_start, dt_end]
    que cae en el período nocturno, definido como de 22:00 a 06:00 del día siguiente.
    Se considera que si el reporte ocurre en un solo día y está entre 00:00 y 06:00,
    se calcula usando ese intervalo.
    """
    total = timedelta(0)
    # Si el reporte cruza la medianoche, ajustamos dt_end
    if dt_end <= dt_start:
        dt_end += timedelta(days=1)
    
    # Caso 1: El reporte ocurre en un solo día
    if dt_start.date() == dt_end.date():
        # Si el reporte ocurre en la madrugada (antes de las 06:00)
        if dt_start.hour < 6:
            nocturnal_period = (
                datetime.combine(dt_start.date(), time(0, 0)),
                datetime.combine(dt_start.date(), time(6, 0))
            )
            total += overlap_interval(dt_start, dt_end, *nocturnal_period)
        # Si el reporte ocurre en la noche (a partir de las 22:00)
        if dt_start.hour >= 22:
            nocturnal_period = (
                datetime.combine(dt_start.date(), time(21, 0)),
                datetime.combine(dt_start.date(), time(23, 59, 59))
            )
            total += overlap_interval(dt_start, dt_end, *nocturnal_period)
    else:
        # Reporte que abarca dos días
        # Parte del primer día (a partir de las 22:00)
        nocturnal_first = (
            datetime.combine(dt_start.date(), time(21, 0)),
            datetime.combine(dt_start.date(), time(23, 59, 59))
        )
        total += overlap_interval(dt_start, dt_end, *nocturnal_first)
        # Parte del segundo día (hasta las 06:00)
        nocturnal_second = (
            datetime.combine(dt_end.date(), time(0, 0)),
            datetime.combine(dt_end.date(), time(6, 0))
        )
        total += overlap_interval(dt_start, dt_end, *nocturnal_second)
    return total


