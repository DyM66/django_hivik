# got/models.py
import base64
from dirtyfields import DirtyFieldsMixin
from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from io import BytesIO
import qrcode
from taggit.managers import TaggableManager
from outbound.models import Place
from .paths import *


# Model 1: Activos (Centro de costos)
class Asset(models.Model):
    AREA = (('a', 'Motonave'), ('c', 'Barcazas'), ('o', 'Oceanografía'), ('l', 'Locativo'), ('v', 'Vehiculos'), ('x', 'Apoyo'),)
    abbreviation = models.CharField(max_length=3, unique=True, primary_key=True)
    name = models.CharField(max_length=50)
    area = models.CharField(max_length=1, choices=AREA, default='a')
    supervisor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    capitan = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='Capitanes')

    imagen = models.ImageField(upload_to=get_upload_path, null=True, blank=True)
    show = models.BooleanField(default=True)
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='modified_assets')
    maintenance_compliance_cache = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Valor cacheado de mantenimiento (%)")
    place = models.ForeignKey(Place, on_delete=models.SET_NULL, null=True, blank=True, related_name='assets', help_text='Ubicación asociada (opcional).')

    # Campos para Barcos
    type_vessel = models.CharField(max_length=100, null=True, blank=True)
    type_navigation = models.CharField(max_length=100, null=True, blank=True)
    type_of_trade = models.CharField(max_length=100, null=True, blank=True)

    bandera = models.CharField(default='Colombia', max_length=50, null=True, blank=True)
    eslora = models.DecimalField(default=0, max_digits=8, decimal_places=2, null=True, blank=True)
    manga = models.DecimalField(default=0, max_digits=8, decimal_places=2, null=True, blank=True)
    puntal = models.DecimalField(default=0, max_digits=8, decimal_places=2, null=True, blank=True)
    calado = models.DecimalField(default=0, max_digits=8, decimal_places=2, null=True, blank=True)
    material = models.CharField(max_length=100, null=True, blank=True)
    deadweight = models.IntegerField(default=0, null=True, blank=True)
    arqueo_bruto = models.IntegerField(default=0, null=True, blank=True)
    arqueo_neto = models.IntegerField(default=0, null=True, blank=True)
    potencia = models.DecimalField(default=0, max_digits=8, decimal_places=2, null=True, blank=True, help_text='En kW.')
    anio = models.PositiveIntegerField(null=True, blank=True)
    bollard_pull = models.DecimalField(default=0, max_digits=8, decimal_places=2, null=True, blank=True)

    @property
    def capacidad_fo(self):
        total = Equipo.objects.filter(system__asset=self, tipo='k', tipo_almacenamiento='Combustible').aggregate(total_volumen=models.Sum('volumen'))['total_volumen'] or 0
        return total    

    def calculate_maintenance_compliance(self):
        systems = self.system_set.all()
        all_rutas = Ruta.objects.filter(system__in=systems)
        total_niveles = sum(ruta.nivel for ruta in all_rutas)

        if total_niveles == 0:
            return None

        compliant_weight = 0
        for ruta in all_rutas:
            if ruta.next_date >= date.today():
                compliant_weight += ruta.nivel

        compliance_percentage = (compliant_weight / total_niveles) * 100
        return round(compliance_percentage, 2)

    def update_maintenance_compliance_cache(self):
        new_value = self.calculate_maintenance_compliance()
        self.maintenance_compliance_cache = new_value
        self.save(update_fields=['maintenance_compliance_cache'])

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('got:asset-detail', args=[str(self.abbreviation)])

    class Meta:
        permissions = (('access_all_assets', 'Access all assets'),)
        # permissions = (('can_see_completely', 'Access to completely info'),)
        ordering = ['area', 'name']


# Model 2: Sistemas (Grupos constructivos, Equipos especiales)
class System(models.Model):
    STATUS = (('m', 'Mantenimiento'), ('o', 'Operativo'), ('x', 'Fuera de servicio'), ('s', 'Stand by'))
    name = models.CharField(max_length=50)
    location = models.CharField(max_length=50, default="Cartagena", null=True, blank=True)
    state = models.CharField(choices=STATUS, default='o', max_length=1)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, to_field='abbreviation')
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    
    def __str__(self):
        return '%s/ %s' % (self.asset, self.name)

    def get_absolute_url(self):
        return reverse('got:sys-detail', args=[self.id])

    class Meta:
        ordering = ['asset__name', 'name']


# Model 3: Ordenes de trabajo
class Ot(models.Model):
    STATUS = (('a', 'Abierto'), ('x', 'En ejecución'), ('f', 'Finalizado'), ('c', 'Cancelado'),)
    TIPO_MTTO = (('p', 'Preventivo'), ('c', 'Correctivo'), ('m', 'Modificativo'),)
    creation_date = models.DateField(auto_now_add=True)
    num_ot = models.AutoField(primary_key=True)
    system = models.ForeignKey(System, on_delete=models.CASCADE)
    description = models.TextField()
    supervisor = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(choices=STATUS, default='x', max_length=1)
    tipo_mtto = models.CharField(choices=TIPO_MTTO, max_length=1)
    sign_supervision = models.ImageField(upload_to=get_upload_path, null=True, blank=True)
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='modified_ots')

    closing_date = models.DateField(null=True, blank=True)

    def all_tasks_finished(self):
        related_tasks = self.task_set.all()
        if all(task.finished for task in related_tasks):
            return True
        return False

    def __str__(self):
        return '%s - %s' % (self.num_ot, self.description)

    def get_absolute_url(self):
        return reverse('got:ot-detail', args=[str(self.num_ot)])
    
    def save(self, *args, **kwargs):
        # Si ya existe la OT, obtenemos la instancia anterior
        if self.pk:
            old = Ot.objects.get(pk=self.pk)
            # Si el estado pasa de algo distinto a 'f' a 'f' y no se ha registrado la fecha de cierre
            if old.state != 'f' and self.state == 'f' and not self.closing_date:
                self.closing_date = timezone.now().date()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-num_ot']


# Model 4
class Equipo(DirtyFieldsMixin, models.Model):
    TIPO = (
        ('a', 'Climatización'),
        ('b', 'Bomba'),
        ('c', 'Compresor'),
        ('d', 'Grúa'),
        ('e', 'Motor eléctrico'),
        ('f', 'Emergencias'),
        ('g', 'Generador'),
        ('h', 'Cilindro hidráulico'),
        ('i', 'Instrumentos y herramientas'),
        ('j', 'Distribución eléctrica'),
        ('k', 'Tanque de almacenamiento'),
        ('l', 'Gobierno'),
        ('m', 'Comunicación'),
        ('n', 'Navegación'),
        ('o', 'Maniobras'),
        ('p', 'Habitabilidad'),
        ('q', 'Informatica y vigilacia'),
        ('nr', 'No rotativo'),
        ('r', 'Motor a combustión'),    
        ('t', 'Transmisión'),
        ('u', 'Unidad Hidráulica'),
        ('v', 'Valvula'),
        ('w', 'Winche'),
        ('x', 'Estructuras'),
        ('y', 'Soporte de vida'),
        ('z', 'Banco de baterias'),
    )

    ESTADO = (('b', 'BUEN ESTADO'), ('m', 'MAL ESTADO'), ('f', 'FUERA DE SERVICIO'),)
    code = models.CharField(primary_key=True, max_length=50)
    name = models.CharField("Nombre", max_length=100)
    date_inv = models.DateField("Fecha de ingreso", auto_now_add=True)
    model = models.CharField("Modelo", max_length=50, null=True, blank=True)
    serial = models.CharField("Serial", max_length=50, null=True, blank=True)
    marca = models.CharField("Marca", max_length=50, null=True, blank=True)
    fabricante = models.CharField("Fabricante", max_length=50, null=True, blank=True)
    feature = models.TextField("Caracteristicas")
    tipo = models.CharField("Categoria", choices=TIPO, default='nr', max_length=2)
    estado = models.CharField("Estado", choices=ESTADO, default='b', max_length=1)
    system = models.ForeignKey(System, on_delete=models.CASCADE, related_name='equipos')
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
        if self.tipo != 'r':
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


# Model 5: Historial de horas de equipos/ Kilometros
class HistoryHour(models.Model): # Agregar un campo para llevar el registro del total
    report_date = models.DateField()
    hour = models.DecimalField(max_digits=10, decimal_places=2)
    reporter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    component = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='hours')
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='modified_hours')

    def __str__(self):
        return '%s: %s - %s (%s) /%s' % (self.report_date, self.component, self.hour, self.reporter, self.component.system.asset)

    class Meta:
        ordering = ['-report_date']
        unique_together = ('component', 'report_date')


# Model 6: Rutinas de mantenimiento
class Ruta(models.Model):
    CONTROL = (('d', 'Días'), ('h', 'Horas'), ('k', 'Kilómetros'))
    NIVEL = ((1, 'Nivel 1 - Operadores'), (2, 'Nivel 2 - Técnico'), (3, 'Nivel 3 - Proveedor especializado'))
    code = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    control = models.CharField(choices=CONTROL, max_length=1)
    frecuency = models.IntegerField()
    intervention_date = models.DateField()
    nivel = models.IntegerField(choices=NIVEL, default=1)
    ot = models.ForeignKey(Ot, on_delete=models.SET_NULL, null=True, blank=True)
    system = models.ForeignKey(System, on_delete=models.CASCADE, related_name='rutas')
    equipo = models.ForeignKey(Equipo, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipos')
    dependencia = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='dependiente')
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    # Diques
    clase_date = models.DateField(null=True, blank=True, help_text="(Opcional) Fecha en que se renovó el certificado de clase, si es un dique de clase.")

    @property
    def dique_window(self):
        # 1) sólo aplica si name = 'Dique'
        if self.name.lower() != 'dique':
            return None

        # 2) si no hay clase_date => no calculamos nada
        if not self.clase_date:
            return None
        
        delta_days = abs((self.intervention_date - self.clase_date).days)
        clase_threshold = 365
        last_was_clase = (delta_days <= clase_threshold)

        HALF_YEAR = timedelta(days=182)   # ~6 meses
        TWO_HALF_YEARS = timedelta(days=913)  # ~2.5 años
        FIVE_YEARS = timedelta(days=1826)     # ~5 años

        mid_point = self.clase_date + TWO_HALF_YEARS
        start = mid_point - HALF_YEAR
        end = mid_point + HALF_YEAR
        final = self.clase_date + FIVE_YEARS

        if last_was_clase:
            dique_type = 'Proximo Dique intermedio: ventana intermedia a 2.5 años ± 6 meses'
        else: 
            dique_type = 'Proximo Dique de clase: fecha de clase + 5 años exactos'
        return {'start': start, 'end': end, 'final': final, 'dique_type': dique_type}

    @property
    def next_date(self):
        if self.control == 'd':
            ndays = self.frecuency
            return self.intervention_date + timedelta(days=ndays)
        
        if (self.control == 'h') and not self.ot:
            inv = self.frecuency - self.equipo.horometro
            if self.equipo.prom_hours < 2:
                ndays = int(inv/2)
            else:
                ndays = int(inv/self.equipo.prom_hours)
        
        elif self.control == 'h' or self.control == 'k':
            period = self.equipo.hours.filter(report_date__gte=self.intervention_date, report_date__lte=date.today()).aggregate(total_hours=models.Sum('hour'))['total_hours'] or 0
            inv = self.frecuency - period
            if self.equipo.prom_hours < 2:
                ndays = int(inv/2)
            else:
                ndays = int(inv/self.equipo.prom_hours)
            # try:
            #     ndays = int(inv/self.equipo.prom_hours)
            # except (ZeroDivisionError, AttributeError):
            #     ndays = int(inv/12)
        MAX_DAYS = 365 * 10
        if ndays > MAX_DAYS:
            ndays = MAX_DAYS
        return date.today() + timedelta(days=ndays)

    @property
    def daysleft(self):
        if self.control == 'd':
            return (self.next_date - date.today()).days
        else:
            return int(self.frecuency - (self.equipo.hours.filter(report_date__gte=self.intervention_date, report_date__lte=date.today()).aggregate(total_hours=models.Sum('hour'))['total_hours'] or 0))

    @property
    def percentage_remaining(self):
        if self.control == 'd':
            time_remaining = (self.next_date - date.today()).days

        elif self.control == 'h' or self.control == 'k':
            hours_period = (self.equipo.hours.filter(
                    report_date__gte=self.intervention_date,
                    report_date__lte=date.today()
                ).aggregate(total_hours=models.Sum('hour'))['total_hours']) or 0
            
            time_remaining = self.frecuency - hours_period

        return int((time_remaining / self.frecuency) * 100)

    def __str__(self):
        return '%s - %s' % (self.system, self.name)

    def get_absolute_url(self):
        return reverse('got:sys-detail', args=[str(self.system.id)])

    class Meta:
        ordering = ['control', 'frecuency', 'equipo__name']


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


# class ActivityHistory(models.Model):
#     task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='history_notes')
#     note = models.TextField(help_text="Descripción de la novedad o incidencia registrada")
#     created_at = models.DateField(auto_now_add=True, help_text="Fecha en la que se registró la novedad")
#     created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_history', help_text="Usuario que registró la novedad")

#     class Meta:
#         ordering = ['-created_at']
#         verbose_name = "Registro de Novedad"
#         verbose_name_plural = "Registros de Novedades"

#     def __str__(self):
#         # Muestra la actividad, la fecha y los primeros 50 caracteres de la nota
#         return f"Novedad en '{self.task}' el {self.created_at}: {self.note[:50]}..."
        
#     def get_absolute_url(self):
#         return reverse('mto:activity-history-detail', args=[str(self.id)])


# Model 10: Reportes de falla
class FailureReport(models.Model):
    IMPACT = (('s', 'La seguridad personal'), ('m', 'El medio ambiente'), ('i', 'Integridad del equipo/sistema'), ('o', 'El desarrollo de las operaciones'),)
    report = models.CharField(max_length=100, null=True, blank=True)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, null=True, blank=True)
    moment = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    causas = models.TextField()
    suggest_repair = models.TextField(null=True, blank=True)
    critico = models.BooleanField()
    closed = models.BooleanField(default=False)
    impact = ArrayField(models.CharField(max_length=1, choices=IMPACT), default=list, blank=True)
    related_ot = models.ForeignKey('Ot', on_delete=models.SET_NULL, null=True, blank=True, related_name='failure_report')
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='modified_failures')

    class Meta:
        ordering = ['-moment']

    def __str__(self):
        status = "Cerrado" if self.closed else "Abierto"
        status2 = self.equipo.name if self.equipo else ""
        return f'{self.id} - Reporte de falla en {status2} - {status}'

    def get_absolute_url(self):
        return reverse('got:failure-report-detail', kwargs={'pk': self.pk})

    def get_impact_display(self, impact_code):
        return dict(self.IMPACT).get(impact_code, "Desconocido")


# Model 14: Suministros (Inventario para barcos o bodegas, contenido de equipos o ...)
class Suministro(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00')) 
    Solicitud = models.ForeignKey('inv.solicitud', on_delete=models.CASCADE, null=True, blank=True) #Obsoleto
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, null=True, blank=True, related_name='suministros')
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, null=True, blank=True, related_name='suministros')

    def __str__(self):
        return f"{self.cantidad} {self.item.presentacion} - {self.item} "


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

    asset = models.ForeignKey(Asset, related_name='documents', on_delete=models.CASCADE, null=True, blank=True)
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
