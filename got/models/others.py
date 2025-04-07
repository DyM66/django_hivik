# got/models.py
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from taggit.managers import TaggableManager

from got.models.routine import Ruta
from got.models.equipment import Equipo
from got.models.work_order import Ot
from got.models.failure_report import FailureReport
from got.paths import *


# Model 7: Servicios
class Item(models.Model):
    SECCION = (('c', 'Consumibles'), ('h', 'Herramientas y Elementos'), ('r', 'Repuestos'))
    name = models.CharField(max_length=50)
    reference = models.CharField(max_length=100, null=True, blank=True)
    imagen = models.ImageField(upload_to=get_upload_path, null=True, blank=True)
    presentacion = models.CharField(max_length=10)
    code = models.CharField(max_length=50, null=True, blank=True)
    seccion = models.CharField(max_length=1, choices=SECCION, default='c')
    unit_price = models.DecimalField(max_digits=18, decimal_places=2, default=0.00) 
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.name} {self.reference}"

    class Meta:
        ordering = ['name', 'reference']


# Model 8: Servicios
class Service(models.Model):
    description = models.CharField(max_length=200, unique=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.description

    class Meta:
        ordering = ['description']


# Model 9: Requerimientos para realizar rutina de mantenimiento
class MaintenanceRequirement(models.Model):
    TIPO_REQUISITO = (('m', 'Material'), ('h', 'Herramienta/Equipo'), ('s', 'Servicio'),)
    ruta = models.ForeignKey(Ruta, on_delete=models.CASCADE, related_name='requisitos')
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, blank=True)
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True, related_name='maintenance_requirements')
    descripcion = models.CharField(max_length=200, null=True, blank=True)
    tipo = models.CharField(max_length=1, choices=TIPO_REQUISITO)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    costo = models.DecimalField(max_digits=19, decimal_places=2, default=0.00) 

    def __str__(self):
        if self.tipo == 'm' and self.item:
            return f"Material: {self.item.name} - Cantidad: {self.cantidad}"
        elif self.tipo == 's' and self.service:
            return f"Servicio: {self.service.description} - Cantidad: {self.cantidad}"
        elif self.tipo == 'h' and self.item:
            return f"Herramienta/Equipo: {self.item.name} - Cantidad: {self.cantidad}"
        else:
            return f"Requerimiento: {self.descripcion} - Cantidad: {self.cantidad}"

    def clean(self):
        if self.tipo in ['m', 'h']:
            if not self.item:
                raise ValidationError('Para tipo Material/Herramienta, debe asociarse a un Item.')
            if self.service:
                raise ValidationError('No puede asociar un Service a un requerimiento de tipo Material/Herramienta.')
        elif self.tipo == 's':
            if not self.service:
                raise ValidationError('Para tipo Servicio, debe asociarse a un Service.')
            if self.item:
                raise ValidationError('No puede asociar un Item a un requerimiento de tipo Servicio.')
        else:
            raise ValidationError('Tipo de requerimiento no válido.')
        
    def total_cost(self):
        if self.tipo in ['m', 'h'] and self.item:
            return self.cantidad * self.item.unit_price
        elif self.tipo == 's' and self.service:
            return self.cantidad * self.service.unit_price
        return Decimal('0.00')
    
    def get_absolute_url(self):
        return reverse('got:ruta_detail', args=[str(self.pk)])


# Model 10: Actividades (para OT o Rutinas de mantenimiento)
class Task(models.Model):
    ot = models.ForeignKey(Ot, on_delete=models.CASCADE, null=True, blank=True)
    ruta = models.ForeignKey(Ruta, on_delete=models.CASCADE, null=True, blank=True)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, null=True, blank=True) #En prueba
    responsible = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField()
    procedimiento = models.TextField(default="", blank=True, null=True)
    hse = models.TextField(default="", blank=True, null=True)
    news = models.TextField(blank=True, null=True)
    priority = models.IntegerField(default=0, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    men_time = models.IntegerField(default=0)
    finished = models.BooleanField()
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='modified_tasks')

    @property
    def is_overdue(self):
        overdue_date = self.start_date + timedelta(days=self.men_time)
        return self.start_date and date.today() > overdue_date

    @property
    def final_date(self):
        return self.start_date + timedelta(days=self.men_time)

    def __str__(self):
        return self.description
 
    class Meta:
        permissions = (('can_reschedule_task', 'Reprogramar actividades'), ('can_modify_any_task', 'Can modify any task'),)
        ordering = ['-priority', '-start_date']



# Model 16: Registro estimado de reportes de combustible
class DailyFuelConsumption(models.Model):
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='fuel_consumptions')
    fecha = models.DateField(default=timezone.now)
    com_estimado_motor = models.DecimalField(max_digits=1000, decimal_places=2, default=0)

    class Meta:
        unique_together = ('equipo', 'fecha')
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.equipo}: {self.com_estimado_motor} - {self.fecha}'


# Model 17: Imagenes
class Image(models.Model):
    image = models.ImageField(upload_to=get_upload_path)
    creation = models.DateField(auto_now_add=True)
    failure = models.ForeignKey(FailureReport, related_name='images', on_delete=models.CASCADE, null=True, blank=True)
    equipo = models.ForeignKey(Equipo, related_name='images', on_delete=models.CASCADE, null=True, blank=True)
    task = models.ForeignKey(Task, related_name='images', on_delete=models.CASCADE, null=True, blank=True)
    salida= models.ForeignKey('outbound.outbounddelivery', related_name='images', on_delete=models.CASCADE, null=True, blank=True)
    preoperacional = models.ForeignKey('preoperacionales.preoperacional', related_name='images', on_delete=models.CASCADE, null=True, blank=True)
    preoperacionaldiario = models.ForeignKey('preoperacionales.preoperacionaldiario', related_name='images', on_delete=models.CASCADE, null=True, blank=True)
    darbaja = models.ForeignKey('inv.DarBaja', related_name='images', on_delete=models.CASCADE, null=True, blank=True)


# Model 18: Documentos
class Document(models.Model):
    DOC_TYPES = [
        ('c', 'Certificado'),
        ('f', 'Ficha técnica'),
        ('i', 'Informe'),
        ('m', 'Manual'),
        ('p', 'Plano'),
        ('o', 'Otro'),
    ]

    asset = models.ForeignKey('got.asset', related_name='documents', on_delete=models.CASCADE, null=True, blank=True)
    ot = models.ForeignKey(Ot, related_name='documents', on_delete=models.CASCADE, null=True, blank=True)
    equipo = models.ForeignKey(Equipo, related_name='documents', on_delete=models.CASCADE, null=True, blank=True)
    file = models.FileField(upload_to=get_upload_pdfs)
    description = models.CharField(max_length=200)
    creation = models.DateField(auto_now_add=True)
    doc_type = models.CharField(max_length=1, choices=DOC_TYPES, default='o')
    date_expiry = models.DateField(null=True, blank=True)
    uploaded_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='uploaded_documents')
    tags = TaggableManager(blank=True)

    def __str__(self):
        return self.description

    def clean(self):
        if not (self.asset or self.ot or self.equipo):
            raise ValidationError('El documento debe estar asociado a un asset, OT o equipo.')
        

class ActivityLog(models.Model):
    user_name = models.CharField(max_length=100)
    action = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, null=True, blank=True)
    field_name = models.CharField(max_length=100, null=True, blank=True)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user_name} {self.action} {self.model_name} {self.field_name} at {self.timestamp}"
