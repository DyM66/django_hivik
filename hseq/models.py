from django.db import models
from got.models import Asset
from got.paths import get_upload_path

# Create your models here.
class Permission(models.Model):
    issue_date = models.DateField(auto_now_add=True)
    area = models.OneToOneField(Asset, on_delete=models.CASCADE, null=True, blank=True)
    task = models.TextField('Descripción detallada de la actividad a desarrollar')
    tools = models.TextField('Maquinas, Herramientas y/o equipo a utilizar')
    is_chemical_substances = models.BooleanField(default=False)
    # q1 = 
    # Propiedad dimanica periodo de validez 7 dias


class AuthorizedWorkers(models.Model):
    employee_id = models.ForeignKey('dth.Nomina', on_delete=models.CASCADE)
    sign = models.ImageField(upload_to=get_upload_path, null=True, blank=True)