# inv/models/inventory.py
from django.db import models
from got.models import Equipo, System, Item
from decimal import Decimal
from django.core.validators import FileExtensionValidator

from got.paths import get_upload_path

class Suministro(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00')) 
    Solicitud = models.ForeignKey('inv.solicitud', on_delete=models.CASCADE, null=True, blank=True) #Obsoleto
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, null=True, blank=True, related_name='suministros')
    asset = models.ForeignKey('got.asset', on_delete=models.CASCADE, null=True, blank=True, related_name='suministros')

    def __str__(self):
        return f"{self.cantidad} {self.item.presentacion} - {self.item} "


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


class Transaction(models.Model):
    TIPO = (('i', 'Ingreso'), ('c', 'Consumo'), ('t', 'Transferencia'), ('e', 'Ingreso externo'), ('r', 'Retiro/Baja'))
    suministro = models.ForeignKey(Suministro, on_delete=models.CASCADE, related_name='transacciones')
    cant = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    fecha = models.DateField()
    user = models.CharField(max_length=100)
    motivo = models.TextField(null=True, blank=True)
    tipo = models.CharField(max_length=1, choices=TIPO, default='i')
    cant_report = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True, blank=True) 
    suministro_transf = models.ForeignKey(Suministro, on_delete=models.CASCADE, null=True, blank=True)
    cant_report_transf = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True, blank=True) 

    remision = models.FileField(upload_to=get_upload_path, null=True, blank=True,
        help_text="PDF/Imagen con la remisión del ingreso", validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])]
    )

    # Relación opcional con RetiredSupply
    retired_supply = models.ForeignKey('inv.RetiredSupply', on_delete=models.SET_NULL, null=True, blank=True, related_name='transaction')

    def __str__(self):
        return f"{self.suministro.item.name}: {self.cant}/{self.tipo} el {self.fecha.strftime('%Y-%m-%d')}"

    class Meta:
        permissions = (
            ('can_add_supply', 'Puede añadir suministros'),
            ('can_edit_only_today', 'Puede modificar transacciones SOLO en la fecha actual'),
            )
        constraints = [
            models.UniqueConstraint(fields=['suministro', 'fecha', 'tipo'], name='unique_suministro_fecha_tipo')
        ]