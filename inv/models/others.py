# inv/models/others.py
from django.db import models
from got.paths import *
from got.models import Asset, Ot
from django.contrib.auth.models import User

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