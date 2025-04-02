# dth/models/docs_requests.py

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from dth.models.payroll import Nomina
from dth.models.positions import Document

def get_upload_path_temp(instance, filename):
    # Opcional: Puedes usar una función distinta para guardar los PDF de las solicitudes
    return f"temp_docs/{instance.request.token}/{filename}"

class DocumentRequest(models.Model):
    """
    Representa la "solicitud" de documentos que se le hace a un empleado en una fecha dada.
    """
    # primary_key automático
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    employee = models.ForeignKey(Nomina, on_delete=models.CASCADE, related_name='requests')
    token = models.CharField(max_length=40, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    # Podrías añadir un campo state => (pending, partial, completed), etc.
    # state = models.CharField(...) 

    def __str__(self):
        return f"Solicitud Docs {self.pk} - {self.employee}"

class DocumentRequestItem(models.Model):
    """
    Almacena cada documento solicitado y su información de subida.
    """
    request = models.ForeignKey(DocumentRequest, on_delete=models.CASCADE, related_name='items')
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    pdf_file = models.FileField(upload_to=get_upload_path_temp, blank=True, null=True)
    expiration_date = models.DateField(blank=True, null=True)

    # Campo para indicar aprobación y quién lo verificó
    approved = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"DocRequestItem - {self.document.name} ({self.request.employee.name})"
