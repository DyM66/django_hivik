from datetime import timedelta, datetime, time

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


