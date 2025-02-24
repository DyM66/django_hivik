# inventory_management/models.py
from django.db import models
from got.paths import *
from got.models import Asset, Ot, Equipo, System, Suministro
from django.contrib.auth.models import User
from decimal import Decimal


class DarBaja(models.Model):
    MOTIVO = (
        ('o', 'Obsoleto'),
        ('r', 'Robo/Hurto'),
        ('p', 'Perdida'),
        ('i', 'Inservible/depreciado'),
        ('v', 'Venta'),
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
        db_table = "got_darbaja"
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
        self.last_seq += 1
        self.save(update_fields=['last_seq'])
        return self.last_seq

    def __str__(self):
        return f"{self.asset_abbr}-{self.tipo}: {self.last_seq}"
    

class Transferencia(models.Model):
    fecha = models.DateField(auto_now_add=True)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE)
    responsable = models.CharField(max_length=150)
    receptor = models.CharField(max_length=150)
    origen = models.ForeignKey(System, on_delete=models.CASCADE, related_name='origen')
    destino = models.ForeignKey(System, on_delete=models.CASCADE, related_name='destino')
    observaciones = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha']
        db_table = 'got_transferencia'

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


# Model 13: Solicitudes de compra $app
class Solicitud(models.Model):
    DPTO = (('m', 'Mantenimiento'), ('o', 'Operaciones'),)
    creation_date = models.DateTimeField(auto_now_add=True)
    solicitante = models.ForeignKey(User, on_delete=models.CASCADE)
    requested_by = models.CharField(max_length=100, null=True, blank=True)
    ot = models.ForeignKey(Ot, on_delete=models.CASCADE, null=True, blank=True)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, null=True, blank=True)
    suministros = models.TextField()
    num_sc = models.TextField(null=True, blank=True)
    approved_by = models.CharField(max_length=100, null=True, blank=True)
    approved = models.BooleanField(default=False)
    approval_date = models.DateTimeField(null=True, blank=True) 
    sc_change_date = models.DateTimeField(null=True, blank=True)
    cancel_date = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.TextField(null=True, blank=True)
    cancel = models.BooleanField(default=False)
    satisfaccion = models.BooleanField(default=False)
    recibido_por = models.TextField(null=True, blank=True)
    dpto = models.CharField(choices=DPTO, max_length=1, default='m')

    quotation_file = models.FileField(upload_to=get_upload_pdfs, null=True, blank=True)
    quotation = models.CharField(max_length=200, null=True, blank=True)
    total = models.DecimalField(max_digits=18, decimal_places=2, default=0.00) 

    @property
    def estado(self):
        if self.cancel:
            return 'Cancelado'
        elif self.satisfaccion:
            return 'Recibido'
        elif not self.satisfaccion and self.recibido_por:
            return 'Parcialmente'
        elif self.approved and self.sc_change_date:
            return 'Tramitado'
        elif self.approved:
            return 'Aprobado'
        else:
            return 'No aprobado'

    def __str__(self):
        return f"Suministros para {self.asset}/{self.ot}"
    
    class Meta:
        permissions = (
            ('can_approve', 'Aprobar solicitudes'),
            ('can_cancel', 'Puede cancelar'),
            ('can_view_all_rqs', 'Puede ver todas las solicitudes'),
            ('can_transfer_solicitud', 'Puede transferir solicitudes'),
            )
        ordering = ['-creation_date']
        db_table = 'got_solicitud'