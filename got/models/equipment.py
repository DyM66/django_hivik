import base64
from io import BytesIO
import qrcode

from dirtyfields import DirtyFieldsMixin
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse

from got.models.history_hour import HistoryHour
from got.paths import get_upload_pdfs


class EquipmentType(models.Model):
    code = models.CharField(max_length=5, unique=True, verbose_name="Short Code")
    name_es = models.CharField(max_length=100)  # Nombre en español
    name_en = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True, verbose_name="Descripción")

    def __str__(self):
        return f"{self.code} - {self.name_es}/{self.name_en}"

    class Meta:
        verbose_name = "Tipo de equipo"
        verbose_name_plural = "Tipos de equipos"


class Equipo(DirtyFieldsMixin, models.Model):

    ESTADO = (('b', 'BUEN ESTADO'), ('m', 'MAL ESTADO'), ('f', 'FUERA DE SERVICIO'),)
    code = models.CharField(primary_key=True, max_length=50)
    name = models.CharField("Nombre", max_length=100)
    date_inv = models.DateField("Fecha de ingreso", auto_now_add=True)
    model = models.CharField("Modelo", max_length=50, null=True, blank=True)
    serial = models.CharField("Serial", max_length=50, null=True, blank=True)
    brand = models.CharField("Marca", max_length=50, null=True, blank=True)
    fabricante = models.CharField("Fabricante", max_length=50, null=True, blank=True)
    feature = models.TextField("Caracteristicas")

    type = models.ForeignKey(EquipmentType, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipments',)

    estado = models.CharField("Estado", choices=ESTADO, default='b', max_length=1)
    system = models.ForeignKey('got.system', on_delete=models.CASCADE, related_name='equipos')
    ubicacion = models.CharField(max_length=150, null=True, blank=True)
    critico = models.BooleanField(default=False)
    recomendaciones = models.TextField(null=True, blank=True)
    related = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='related_with')
    qr_code_url = models.URLField(max_length=1000, blank=True, null=True)
    manual_pdf = models.FileField(upload_to=get_upload_pdfs, null=True, blank=True) # Obsoleto
    subsystem = models.CharField(max_length=100, null=True, blank=True) # Obsoleto

    'Motores'
    potencia  = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    initial_hours = models.IntegerField(default=0)
    horometro = models.IntegerField(default=0, null=True, blank=True)
    prom_hours = models.IntegerField(default=0, null=True, blank=True)

    'Tanques'
    tipo_almacenamiento = models.CharField(max_length=100, null=True, blank=True)
    volumen = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    def generate_qr_code(self):
        domain = "https://got.serport.co"
        public_url = f"{domain}/inv/public/equipo/{self.code}/"
        qr = qrcode.QRCode(version=1, box_size=4, border=2)
        qr.add_data(public_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        qr_io = BytesIO()
        img.save(qr_io, format='PNG')
        qr_base64 = base64.b64encode(qr_io.getvalue()).decode('utf-8')
        self.qr_code_url = f"data:image/png;base64,{qr_base64}"

    def save(self, *args, **kwargs):
        if not self.qr_code_url or 'code' in self.get_dirty_fields():
            self.generate_qr_code()
        super().save(*args, **kwargs)

    @property
    def consumo_promedio_por_hora(self): # No funciona correctamente
        '''
        Para equipos de tipo 'r' (motores a combustión) calcula consumo de combustible (articulo con
        ID 132), comparando la fecha de reportes de consumo con la fecha de reporte de horas.
        '''
        if self.type.code != 'r':
            print(f"Equipo {self.code} is not of type 'r'.")
            return None

        # Tomar los últimos 30 registros de consumo de combustible
        consumos = self.fuel_consumptions.order_by('-fecha')[:30]
        total_consumo = consumos.aggregate(models.Sum('com_estimado_motor'))['com_estimado_motor__sum'] or 0
        fechas_consumo = consumos.values_list('fecha', flat=True)
        total_horas = HistoryHour.objects.filter(component=self, report_date__in=fechas_consumo).aggregate(models.Sum('hour'))['hour__sum'] or 0

        if total_horas > 0:
            consumo_promedio = total_consumo / total_horas
            print(f"Average consumption per hour for Equipo {self.code}: {consumo_promedio}")
            return consumo_promedio
        else:
            print(f"No hours recorded for Equipo {self.code} on dates {list(fechas_consumo)}.")
            return None

    def calculate_horometro(self):
        total_hours = self.hours.aggregate(total=models.Sum('hour'))['total'] or 0
        return total_hours + self.initial_hours
    
    def last_hour_report_date(self):
        last_report = self.hours.order_by('-report_date').first()
        return last_report.report_date if last_report else None

    def __str__(self):
        return f"{self.system.asset} - {self.name}"

    class Meta:
        ordering = ['name', 'code']

    def get_absolute_url(self):
        return reverse('got:equipo-detail', args=[self.code])
    

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