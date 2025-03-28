from django.db import models
from got.models import Equipo, System, Suministro
from decimal import Decimal


class Transference(models.Model):
    fecha = models.DateField(auto_now_add=True)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE)
    responsable = models.CharField(max_length=150)
    receptor = models.CharField(max_length=150)
    origen = models.ForeignKey(System, on_delete=models.CASCADE, related_name='origen')
    destino = models.ForeignKey(System, on_delete=models.CASCADE, related_name='destino')
    observaciones = models.TextField(null=True, blank=True)
    signature = models.ImageField(upload_to='transference_signatures/', null=False, blank=False, help_text='Firma obligatoria en formato de imagen (jpg, png, etc.)')

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.equipo} - {self.origen} -> {self.destino}"


# Model 15: Registro de movimientos de suminsitros realizados en los barcos o bodegas locativas
class Transaction(models.Model):
    TIPO = (('i', 'Ingreso'), ('c', 'Consumo'), ('t', 'Transferencia'), ('e', 'Ingreso externo'),)
    suministro = models.ForeignKey(Suministro, on_delete=models.CASCADE, related_name='transacciones')
    cant = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    fecha = models.DateField()
    user = models.CharField(max_length=100)
    motivo = models.TextField(null=True, blank=True)
    tipo = models.CharField(max_length=1, choices=TIPO, default='i')
    cant_report = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True, blank=True) 
    suministro_transf = models.ForeignKey(Suministro, on_delete=models.CASCADE, null=True, blank=True)
    cant_report_transf = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True, blank=True) 

    def __str__(self):
        return f"{self.suministro.item.name}: {self.cant}/{self.tipo} el {self.fecha.strftime('%Y-%m-%d')}"

    class Meta:
        permissions = (('can_add_supply', 'Puede añadir suministros'),)
        constraints = [
            models.UniqueConstraint(fields=['suministro', 'fecha', 'tipo'], name='unique_suministro_fecha_tipo')
        ]
        db_table = 'got_transaction'