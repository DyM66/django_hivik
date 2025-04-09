# inv/models/equipment_retirement.py
from django.db import models
from got.paths import get_upload_path
from django.contrib.auth.models import User
from inv.models.inventory import Suministro

MOTIVO = (('o', 'Obsoleto'), ('r', 'Robo/Hurto'), ('p', 'Perdida'), ('v', 'Venta'), ('x', 'Otro'),)

class DarBaja(models.Model):
    
    fecha = models.DateField(auto_now_add=True)
    reporter = models.CharField(max_length=100)
    responsable = models.CharField(max_length=100)
    equipo = models.ForeignKey('got.Equipo', on_delete=models.CASCADE)
    activo = models.CharField(max_length=150)
    motivo = models.CharField(max_length=1, choices=MOTIVO)
    observaciones = models.TextField()
    disposicion = models.TextField()
    firma_responsable = models.ImageField(upload_to=get_upload_path)
    firma_autorizado = models.ImageField(upload_to=get_upload_path)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.activo}/{self.equipo} - {self.fecha}"
    

class RetiredSupply(models.Model):
    date = models.DateField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='retiros_suministro')
    supervisor = models.CharField(max_length=100)
    supply = models.ForeignKey(Suministro, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=1, choices=MOTIVO)
    remark = models.TextField(null=True, blank=True)
    provision = models.TextField(null=True, blank=True)

    responsible_signature = models.ImageField(upload_to=get_upload_path, null=True, blank=True)
    authorized_signature = models.ImageField(upload_to=get_upload_path, null=True, blank=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Baja de {self.supply.item.name} [{self.amount}] - {self.date}"
    

class RetiredSupplyImage(models.Model):
    image = models.ImageField(upload_to=get_upload_path)
    creation = models.DateField(auto_now_add=True)
    retired_supply = models.ForeignKey(RetiredSupply, related_name='images', on_delete=models.CASCADE)

    def __str__(self):
        return f"Imagen de retiro {self.retired_supply.pk} - {self.pk}"