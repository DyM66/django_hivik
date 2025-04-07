from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.urls import reverse
from django.contrib.auth.models import User

from got.models.equipment import Equipo

class FailureReport(models.Model):
    IMPACT = (('s', 'La seguridad personal'), ('m', 'El medio ambiente'), ('i', 'Integridad del equipo/sistema'), ('o', 'El desarrollo de las operaciones'),)
    report = models.CharField(max_length=100, null=True, blank=True)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, null=True, blank=True)
    moment = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    causas = models.TextField()
    suggest_repair = models.TextField(null=True, blank=True)
    critico = models.BooleanField()
    closed = models.BooleanField(default=False)
    impact = ArrayField(models.CharField(max_length=1, choices=IMPACT), default=list, blank=True)
    related_ot = models.ForeignKey('Ot', on_delete=models.SET_NULL, null=True, blank=True, related_name='failure_report')
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='modified_failures')

    class Meta:
        ordering = ['-moment']

    def __str__(self):
        status = "Cerrado" if self.closed else "Abierto"
        status2 = self.equipo.name if self.equipo else ""
        return f'{self.id} - Reporte de falla en {status2} - {status}'

    def get_absolute_url(self):
        return reverse('got:failure-report-detail', kwargs={'pk': self.pk})

    def get_impact_display(self, impact_code):
        return dict(self.IMPACT).get(impact_code, "Desconocido")