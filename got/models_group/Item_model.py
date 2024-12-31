from django.db import models
from django.contrib.auth.models import User
from got.paths import *


# Model 3: Articulos
class Item(models.Model):
    SECCION = (('c', 'Consumibles'), ('h', 'Herramientas y equipos'), ('r', 'Repuestos'))
    name = models.CharField(max_length=50)
    reference = models.CharField(max_length=100, null=True, blank=True)
    imagen = models.ImageField(upload_to=get_upload_path, null=True, blank=True)
    presentacion = models.CharField(max_length=10)
    code = models.CharField(max_length=50, null=True, blank=True)
    seccion = models.CharField(max_length=1, choices=SECCION, default='c')
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, default=0.00) 
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.name} {self.reference}"

    class Meta:
        ordering = ['name', 'reference']