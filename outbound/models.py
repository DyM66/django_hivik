from django.db import models
from datetime import datetime
from got.paths import *
from django.core.validators import RegexValidator


class Place(models.Model):
    name = models.CharField(max_length=200, unique=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, help_text="Latitud de la ubicación.", null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, help_text="Longitude de la ubicación.", null=True, blank=True)
    contact_person = models.CharField(max_length=100, null=True, blank=True)
    contact_phone = models.CharField(max_length=15, validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Número de teléfono inválido.")], null=True, blank=True)
    direccion = models.CharField(max_length=200)
    city = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'outbound_place'
        verbose_name = 'Lugar'
        verbose_name_plural = 'Lugares'


# Model 17: Salidas de articulos de la empresa $app
class OutboundDelivery(models.Model):
    destination = models.ForeignKey(Place, on_delete=models.SET_NULL, null=True, blank=True, related_name='outbound_deliveries')
    destino = models.CharField(max_length=200, null=True, blank=True)
    fecha = models.DateField(auto_now_add=True)
    motivo = models.TextField()
    propietario = models.CharField(max_length=100)
    responsable = models.CharField(max_length=100)
    recibe = models.CharField(max_length=100)
    vehiculo = models.CharField(max_length=100, null=True, blank=False)
    auth = models.BooleanField(default=False)
    sign_recibe = models.ImageField(upload_to=get_upload_path, null=True, blank=True)
    adicional = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.motivo} - {self.fecha}"
    
    class Meta:
        db_table = 'got_salida'
        permissions = (('can_approve_it', 'Aprobar salidas'), )
        ordering = ['-fecha']