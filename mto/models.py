# mto/models.py

from django.db import models
from django.urls import reverse

class MaintenancePlan(models.Model):
    ruta = models.ForeignKey('got.Ruta', on_delete=models.CASCADE, related_name='maintenance_plans', help_text="Ruta asociada a este plan de mantenimiento")
    base_intervention_date = models.DateField(help_text="Fecha de intervención de la ruta en el momento de crear el plan (valor inmutable por defecto)")
    start_count_date = models.DateField(help_text="Fecha de inicio de conteo para el plan. Inicialmente igual a base_intervention_date, pero se puede modificar manualmente")
    period_start = models.DateField(help_text="Inicio del periodo de planificación")
    period_end = models.DateField(help_text="Fin del periodo de planificación")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Plan de {self.ruta.name} ({self.period_start} - {self.period_end})"

    def get_absolute_url(self):
        return reverse('mto:plan-detail', args=[str(self.id)])
