from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse

from datetime import date, timedelta

class Ruta(models.Model):
    CONTROL = (('d', 'Días'), ('h', 'Horas'), ('k', 'Kilómetros'))
    NIVEL = ((1, 'Nivel 1 - Operadores'), (2, 'Nivel 2 - Técnico'), (3, 'Nivel 3 - Proveedor especializado'))
    code = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    control = models.CharField(choices=CONTROL, max_length=1)
    frecuency = models.IntegerField()
    intervention_date = models.DateField()
    nivel = models.IntegerField(choices=NIVEL, default=1)
    ot = models.ForeignKey('got.ot', on_delete=models.SET_NULL, null=True, blank=True)
    system = models.ForeignKey('got.system', on_delete=models.CASCADE, related_name='rutas')
    equipo = models.ForeignKey('got.equipo', on_delete=models.SET_NULL, null=True, blank=True, related_name='equipos')
    dependencia = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='dependiente')
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    # Diques
    clase_date = models.DateField(null=True, blank=True, help_text="(Opcional) Fecha en que se renovó el certificado de clase, si es un dique de clase.")

    @property
    def dique_window(self):
        # 1) sólo aplica si name = 'Dique'
        if self.name.lower() != 'dique':
            return None

        # 2) si no hay clase_date => no calculamos nada
        if not self.clase_date:
            return None
        
        delta_days = abs((self.intervention_date - self.clase_date).days)
        clase_threshold = 365
        last_was_clase = (delta_days <= clase_threshold)

        HALF_YEAR = timedelta(days=182)   # ~6 meses
        TWO_HALF_YEARS = timedelta(days=913)  # ~2.5 años
        FIVE_YEARS = timedelta(days=1826)     # ~5 años

        mid_point = self.clase_date + TWO_HALF_YEARS
        start = mid_point - HALF_YEAR
        end = mid_point + HALF_YEAR
        final = self.clase_date + FIVE_YEARS

        if last_was_clase:
            dique_type = 'Proximo Dique intermedio: ventana intermedia a 2.5 años ± 6 meses'
        else: 
            dique_type = 'Proximo Dique de clase: fecha de clase + 5 años exactos'
        return {'start': start, 'end': end, 'final': final, 'dique_type': dique_type}

    @property
    def next_date(self):
        if self.control == 'd':
            ndays = self.frecuency
            return self.intervention_date + timedelta(days=ndays)
        
        if (self.control == 'h') and not self.ot:
            inv = self.frecuency - self.equipo.horometro
            if self.equipo.prom_hours < 2:
                ndays = int(inv/2)
            else:
                ndays = int(inv/self.equipo.prom_hours)
        
        elif self.control == 'h' or self.control == 'k':
            period = self.equipo.hours.filter(report_date__gte=self.intervention_date, report_date__lte=date.today()).aggregate(total_hours=models.Sum('hour'))['total_hours'] or 0
            inv = self.frecuency - period
            if self.equipo.prom_hours < 2:
                ndays = int(inv/2)
            else:
                ndays = int(inv/self.equipo.prom_hours)
            # try:
            #     ndays = int(inv/self.equipo.prom_hours)
            # except (ZeroDivisionError, AttributeError):
            #     ndays = int(inv/12)
        MAX_DAYS = 365 * 10
        if ndays > MAX_DAYS:
            ndays = MAX_DAYS
        return date.today() + timedelta(days=ndays)

    @property
    def daysleft(self):
        if self.control == 'd':
            return (self.next_date - date.today()).days
        else:
            return int(self.frecuency - (self.equipo.hours.filter(report_date__gte=self.intervention_date, report_date__lte=date.today()).aggregate(total_hours=models.Sum('hour'))['total_hours'] or 0))

    @property
    def percentage_remaining(self):
        if self.control == 'd':
            time_remaining = (self.next_date - date.today()).days

        elif self.control == 'h' or self.control == 'k':
            hours_period = (self.equipo.hours.filter(
                    report_date__gte=self.intervention_date,
                    report_date__lte=date.today()
                ).aggregate(total_hours=models.Sum('hour'))['total_hours']) or 0
            
            time_remaining = self.frecuency - hours_period

        return int((time_remaining / self.frecuency) * 100)

    def __str__(self):
        return '%s - %s' % (self.system, self.name)

    def get_absolute_url(self):
        return reverse('got:sys-detail', args=[str(self.system.id)])

    class Meta:
        ordering = ['control', 'frecuency', 'equipo__name']