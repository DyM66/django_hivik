# inventory_management/models.py
from django.db import models
from got.paths import *

class DarBaja(models.Model):
    MOTIVO = (
        ('o', 'Obsoleto'),
        ('r', 'Robo/Hurto'),
        ('p', 'Perdida'),
        ('i', 'Inservible/depreciado')
    )
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
        db_table = "got_darbaja"   # la misma tabla
        # managed = False            # para que Django no intente crear/borrar la tabla
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.activo}/{self.equipo} - {self.fecha}"
    


class EquipoCodeCounter(models.Model):
    asset_abbr = models.CharField(max_length=50)
    tipo = models.CharField(max_length=2)
    last_seq = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('asset_abbr', 'tipo')
        verbose_name = 'Contador de Código de Equipo'
        verbose_name_plural = 'Contadores de Código de Equipo'

    def increment_seq(self):
        """
        Incrementa el contador de secuencia y retorna el nuevo valor.
        """
        self.last_seq += 1
        self.save(update_fields=['last_seq'])
        return self.last_seq

    def __str__(self):
        return f"{self.asset_abbr}-{self.tipo}: {self.last_seq}"