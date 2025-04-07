from django.db import models

from django.contrib.auth.models import User

class HistoryHour(models.Model): # Agregar un campo para llevar el registro del total
    report_date = models.DateField()
    hour = models.DecimalField(max_digits=10, decimal_places=2)
    reporter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    component = models.ForeignKey('got.equipo', on_delete=models.CASCADE, related_name='hours')
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='modified_hours')

    def __str__(self):
        return '%s: %s - %s (%s) /%s' % (self.report_date, self.component, self.hour, self.reporter, self.component.system.asset)

    class Meta:
        ordering = ['-report_date']
        unique_together = ('component', 'report_date')