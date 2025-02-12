# mto/models.py
from django.db import models
from django.urls import reverse

class MaintenancePlan(models.Model):
    ruta = models.ForeignKey('got.Ruta', on_delete=models.CASCADE, related_name='maintenance_plans', help_text="Ruta asociada a este plan de mantenimiento")
    start_count_date = models.DateField(help_text="Fecha de inicio de conteo para el plan. Inicialmente igual a base_intervention_date, pero se puede modificar manualmente")
    period_start = models.DateField(help_text="Inicio del periodo de planificación")
    period_end = models.DateField(help_text="Fin del periodo de planificación")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Plan de {self.ruta.name} ({self.period_start} - {self.period_end})"

    def get_absolute_url(self):
        return reverse('mto:plan-detail', args=[str(self.id)])
    

class MaintenancePlanEntry(models.Model):
    plan = models.ForeignKey(MaintenancePlan, on_delete=models.CASCADE, related_name='entries')
    month = models.PositiveSmallIntegerField(help_text="Mes (1-12)")
    year = models.PositiveSmallIntegerField(help_text="Año")
    planned_executions = models.PositiveIntegerField(default=0, help_text="Número de ejecuciones planificadas para este mes")
    actual_executions = models.PositiveIntegerField(default=0, help_text="Número de ejecuciones reales registradas en este mes")
    # Opcional: podrías agregar un campo para guardar las fechas de cada ejecución,
    # por ejemplo, un JSONField que almacene una lista de fechas, si lo requieres.
    # execution_dates = models.JSONField(null=True, blank=True)

    class Meta:
        unique_together = ('plan', 'month', 'year')
        ordering = ['year', 'month']

    def __str__(self):
        return f"{self.month}/{self.year} - Plan: {self.planned_executions} / Real: {self.actual_executions}"

