from django.db import models
import uuid
from datetime import datetime

def get_upload_path(instance, filename):

    ext = filename.split('.')[-1]
    filename = f"media/{datetime.now():%Y%m%d%H%M%S}-{uuid.uuid4()}.{ext}"
    return filename


# Model 17: Salidas de articulos de la empresa $app
class OutboundDelivery(models.Model):

    destino = models.CharField(max_length=200)
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
        managed = False 
        permissions = (('can_approve_it', 'Aprobar salidas'), )
        ordering = ['-fecha']