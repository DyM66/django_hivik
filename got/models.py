from datetime import date, timedelta, datetime
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Sum, Count
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
import uuid
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import number_format
from django.utils.translation import gettext as _
from decimal import Decimal
from preoperacionales.models import Preoperacional, PreoperacionalDiario


# Funciones auxiliares
def get_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"media/{datetime.now():%Y%m%d%H%M%S}-{uuid.uuid4()}.{ext}"
    return filename


def get_upload_pdfs(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"pdfs/{uuid.uuid4()}.{ext}"
    return filename


# Model 1: Registro de actividades
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


# Model 2: Carasteristicas del usuario
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    cargo = models.CharField(max_length=100, null=True, blank=True)
    firma = models.ImageField(upload_to=get_upload_path, null=True, blank=True)
    station = models.CharField(max_length=100, null=True, blank=True)
    cedula = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


# Model 3: Articulos
class Item(models.Model):
    SECCION = (('c', 'Consumibles'), ('h', 'Herramientas y equipos'), ('r', 'Repuestos'))
    name = models.CharField(max_length=50)
    reference = models.CharField(max_length=100, null=True, blank=True)
    imagen = models.ImageField(upload_to=get_upload_path, null=True, blank=True)
    presentacion = models.CharField(max_length=10)
    code = models.CharField(max_length=50, null=True, blank=True)
    seccion = models.CharField(max_length=1, choices=SECCION, default='c')
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.name} {self.reference}"

    class Meta:
        ordering = ['name', 'reference']
        

# Model 4: Activos (Centro de costos)
class Asset(models.Model):
    AREA = (
        ('a', 'Motonave'),
        ('b', 'Buceo'),
        ('c', 'Barcazas'),
        ('o', 'Oceanografía'),
        ('l', 'Locativo'),
        ('v', 'Vehiculos'),
        ('x', 'Apoyo'),
    )
    abbreviation = models.CharField(max_length=3, unique=True, primary_key=True)
    name = models.CharField(max_length=50)
    area = models.CharField(max_length=1, choices=AREA, default='a')
    supervisor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    imagen = models.ImageField(upload_to=get_upload_path, null=True, blank=True)
    show = models.BooleanField(default=True)
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='modified_assets')
    # Campos para Barcos
    capitan = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='Capitanes')
    bandera = models.CharField(default='Colombia', max_length=50, null=True, blank=True)
    eslora = models.DecimalField(default=0, max_digits=8, decimal_places=2, null=True, blank=True)
    manga = models.DecimalField(default=0, max_digits=8, decimal_places=2, null=True, blank=True)
    puntal = models.DecimalField(default=0, max_digits=8, decimal_places=2, null=True, blank=True)
    calado_maximo = models.DecimalField(default=0, max_digits=8, decimal_places=2, null=True, blank=True)
    deadweight = models.IntegerField(default=0, null=True, blank=True)
    arqueo_bruto = models.IntegerField(default=0, null=True, blank=True)
    arqueo_neto = models.IntegerField(default=0, null=True, blank=True)

    @property
    def maintenance_compliance(self):
        systems = self.system_set.all()
        all_rutas = Ruta.objects.filter(system__in=systems)
        total_rutas = all_rutas.count()
        
        if total_rutas == 0:
            return '---'

        compliant_count = 0

        for ruta in all_rutas:
            if ruta.control == 'd':
                if ruta.next_date >= date.today():
                    compliant_count += 1
            elif ruta.control == 'h' or ruta.control == 'k':
                accumulated_hours = ruta.equipo.hours.filter(
                    report_date__gte=ruta.intervention_date,
                    report_date__lte=date.today()
                ).aggregate(total_hours=Sum('hour'))['total_hours'] or 0
                
                if accumulated_hours <= ruta.frecuency:
                    compliant_count += 1

        compliance_percentage = (compliant_count / total_rutas) * 100
        return round(compliance_percentage, 2)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('got:asset-detail', args=[str(self.abbreviation)])

    class Meta:
        permissions = (('can_see_completely', 'Access to completely info'),)
        ordering = ['area', 'name']


# Model 5: Sistemas (Grupos constructivos, Equipos especiales)
class System(models.Model):
    STATUS = (
        ('m', 'Mantenimiento'),
        ('o', 'Operativo'),
        ('x', 'Fuera de servicio'),
        ('s', 'Stand by')
    )
    name = models.CharField(max_length=50)
    group = models.IntegerField()
    location = models.CharField(max_length=50, default="Cartagena", null=True, blank=True)
    state = models.CharField(choices=STATUS, default='m', max_length=1)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, to_field='abbreviation')
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    
    def __str__(self):
        return '%s/ %s' % (self.asset, self.name)

    def get_absolute_url(self):
        return reverse('got:sys-detail', args=[self.id])

    class Meta:
        ordering = ['asset__name', 'group']


# Model 6: Ordenes de trabajo
class Ot(models.Model):
    STATUS = (
        ('a', 'Abierto'),
        ('x', 'En ejecución'),
        ('f', 'Finalizado'),
        ('c', 'Cancelado'),
    )
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

    def all_tasks_finished(self):
        related_tasks = self.task_set.all()
        if all(task.finished for task in related_tasks):
            return True
        return False

    def __str__(self):
        return '%s - %s' % (self.num_ot, self.description)

    def get_absolute_url(self):
        return reverse('got:ot-detail', args=[str(self.num_ot)])

    class Meta:
        ordering = ['-num_ot']


# Model 7: Equipos
class Equipo(models.Model):
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

    code = models.CharField(primary_key=True, max_length=50)
    name = models.CharField(max_length=100)
    date_inv = models.DateField(auto_now_add=True)
    model = models.CharField(max_length=50, null=True, blank=True)
    serial = models.CharField(max_length=50, null=True, blank=True)
    marca = models.CharField(max_length=50, null=True, blank=True)
    fabricante = models.CharField(max_length=50, null=True, blank=True)
    feature = models.TextField()
    tipo = models.CharField(choices=TIPO, default='nr', max_length=2)
    system = models.ForeignKey(System, on_delete=models.CASCADE, related_name='equipos')
    related = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='related_with')
    subsystem = models.CharField(max_length=100, null=True, blank=True)
    ubicacion = models.CharField(max_length=150, null=True, blank=True)
    critico = models.BooleanField(default=False)
    recomendaciones = models.TextField(null=True, blank=True)
    manual_pdf = models.FileField(upload_to=get_upload_pdfs, null=True, blank=True)

    'Motores'
    potencia  = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    initial_hours = models.IntegerField(default=0)
    horometro = models.IntegerField(default=0, null=True, blank=True)
    prom_hours = models.IntegerField(default=0, null=True, blank=True)

    'Tanques'
    tipo_almacenamiento = models.CharField(max_length=100, null=True, blank=True)
    volumen = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    
    @property
    def consumo_promedio_por_hora(self):
        '''
        Para equipos de tipo 'r' (motores a combustión) calcula consumo de combustible (articulo con
        ID 132), comparando la fecha de reportes de consumo con la fecha de reporte de horas.
        '''
        if self.tipo != 'r':
            print(f"Equipo {self.code} is not of type 'r'.")
            return None

        # Tomar los últimos 30 registros de consumo de combustible
        consumos = self.fuel_consumptions.order_by('-fecha')[:30]
        total_consumo = consumos.aggregate(Sum('com_estimado_motor'))['com_estimado_motor__sum'] or 0
        fechas_consumo = consumos.values_list('fecha', flat=True)
        total_horas = HistoryHour.objects.filter(component=self, report_date__in=fechas_consumo).aggregate(Sum('hour'))['hour__sum'] or 0

        if total_horas > 0:
            consumo_promedio = total_consumo / total_horas
            print(f"Average consumption per hour for Equipo {self.code}: {consumo_promedio}")
            return consumo_promedio
        else:
            print(f"No hours recorded for Equipo {self.code} on dates {list(fechas_consumo)}.")
            return None

    def calculate_horometro(self):
        total_hours = self.hours.aggregate(total=Sum('hour'))['total'] or 0
        return total_hours + self.initial_hours
    
    def last_hour_report_date(self):
        last_report = self.hours.order_by('-report_date').first()
        return last_report.report_date if last_report else None

    def __str__(self):
        return f"{self.system.asset} - {self.name}"

    class Meta:
        ordering = ['name', 'code']

    def get_absolute_url(self):
        return reverse('got:sys-detail-view', args=[self.system.id, self.code])


# Model 8: Registro de transferencias de equipos
class Transferencia(models.Model):
    fecha = models.DateField(auto_now_add=True)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE)
    responsable = models.CharField(max_length=100)
    origen = models.ForeignKey(System, on_delete=models.CASCADE, related_name='origen')
    destino = models.ForeignKey(System, on_delete=models.CASCADE, related_name='destino')
    observaciones = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.equipo} - {self.origen} -> {self.destino}"
    

# Model 9: Registro de equipos de baja
class DarBaja(models.Model):
    MOTIVO = (('o', 'Obsoleto'), ('r', 'Robo/Hurto'), ('p', 'Perdida'), ('i', 'Inservible/depreciado'))
    fecha = models.DateField(auto_now_add=True)
    reporter = models.CharField(max_length=100)
    responsable = models.CharField(max_length=100)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE)
    activo = models.CharField(max_length=150)
    motivo = models.CharField(max_length=1, choices=MOTIVO)
    observaciones = models.TextField()
    disposicion = models.TextField()
    firma_responsable = models.ImageField(upload_to=get_upload_path)
    firma_autorizado = models.ImageField(upload_to=get_upload_path)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.activo}/{self.equipo} - {self.fecha}"


# Model 10: Historial de horas de equipos con horometro
class HistoryHour(models.Model):

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


class EquipmentHistory(models.Model):
    ASUNTO_CHOICES = (
        ('movement', 'Movimiento'),
        ('part_change', 'Cambio de repuesto/pieza'),
        ('preventive_maintenance', 'Mantenimiento Preventivo'),
        ('corrective_maintenance', 'Mantenimiento Correctivo'),
        ('specialized_intervention', 'Intervención Especializada'),
    )

    equipment = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='histories')
    date = models.DateField()
    subject = models.CharField(max_length=50, choices=ASUNTO_CHOICES)
    annotations = models.TextField(blank=True, null=True)
    reporter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.equipment} - {self.get_subject_display()} on {self.date}"

    class Meta:
        ordering = ['-date']


# Model 10: Rutinas de mantenimiento de equipos
class Ruta(models.Model):

    CONTROL = (
        ('d', 'Días'),
        ('h', 'Horas'),
        ('k', 'Kilómetros')
    )

    NIVEL = (
        (1, 'Nivel 1 - Operadores'),
        (2, 'Nivel 2 - Técnico'),
        (3, 'Nivel 3 - Proveedor especializado'),
        (4, 'Nivel 4 - Fabricante')
    )

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
    astillero = models.CharField(max_length=50, null=True, blank=True)

    @property
    def next_date(self):
        if self.control == 'd':
            ndays = self.frecuency
            return self.intervention_date + timedelta(days=ndays)
        
        if (self.control == 'h') and not self.ot:
            inv = self.frecuency - self.equipo.horometro
            try:
                ndays = int(inv/self.equipo.prom_hours)
            except (ZeroDivisionError, AttributeError):
                ndays = int(inv/12)
        
        elif self.control == 'h' or self.control == 'k':
            period = self.equipo.hours.filter(report_date__gte=self.intervention_date, report_date__lte=date.today()).aggregate(total_hours=Sum('hour'))['total_hours'] or 0
            inv = self.frecuency - period
            try:
                ndays = int(inv/self.equipo.prom_hours)
            except (ZeroDivisionError, AttributeError):
                ndays = int(inv/12)
        MAX_DAYS = 365 * 10
        if ndays > MAX_DAYS:
            ndays = MAX_DAYS
        return date.today() + timedelta(days=ndays)

    @property
    def daysleft(self):
        if self.control == 'd':
            return (self.next_date - date.today()).days
        else:
            return int(self.frecuency - (self.equipo.hours.filter(report_date__gte=self.intervention_date, report_date__lte=date.today()).aggregate(total_hours=Sum('hour'))['total_hours'] or 0))

    @property
    def percentage_remaining(self):
        
        if self.control == 'd':
            time_remaining = (self.next_date - date.today()).days

        elif self.control == 'h' or self.control == 'k':
            hours_period = (self.equipo.hours.filter(
                    report_date__gte=self.intervention_date,
                    report_date__lte=date.today()
                ).aggregate(total_hours=Sum('hour'))['total_hours']) or 0
            
            time_remaining = self.frecuency - hours_period

        return int((time_remaining / self.frecuency) * 100)

    @property
    def maintenance_status(self):
        percentage = self.percentage_remaining
        if not self.ot:
            return 'e'
        elif percentage <= 10 and not self.ot:
            return 'p'
        elif self.ot.state=='x':
            return 'x'
        else:
            if 25 <= percentage <= 100:
                return 'c'
            elif 5 <= percentage <= 24:
                return 'p'
            else:
                return 'v'

    def __str__(self):
        return '%s - %s' % (self.system, self.name)

    def get_absolute_url(self):
        return reverse('got:sys-detail', args=[str(self.system.id)])

    class Meta:
        ordering = ['frecuency']


class MaintenanceRequirement(models.Model):
    TIPO_REQUISITO = (
        ('m', 'Material'),
        ('h', 'Herramienta/Equipo'),
        ('s', 'Servicio'),
    )

    ruta = models.ForeignKey(Ruta, on_delete=models.CASCADE, related_name='requisitos')
    item = models.ForeignKey(Item, on_delete=models.SET_NULL, null=True, blank=True)
    descripcion = models.CharField(max_length=200, null=True, blank=True)
    tipo = models.CharField(max_length=1, choices=TIPO_REQUISITO)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.descripcion or self.item.name} ({self.cantidad})"
    
    def get_absolute_url(self):
        return reverse('got:ruta_detail', args=[str(self.pk)])


# Model 11: Actividades (para OT o Rutinas de mantenimiento)
class Task(models.Model):

    ot = models.ForeignKey(Ot, on_delete=models.CASCADE, null=True, blank=True)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, null=True, blank=True)
    ruta = models.ForeignKey(Ruta, on_delete=models.CASCADE, null=True, blank=True)

    responsible = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.CharField(max_length=50, blank=True, null=True)

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

    def get_absolute_url(self):
        return reverse('got:task-detail', args=[str(self.id)])
 
    class Meta:
        permissions = (
            ('can_reschedule_task', 'Reprogramar actividades'),
            ('can_modify_any_task', 'Can modify any task'),
            )
        ordering = ['-priority', '-start_date'] 


# Model 12: Reportes de falla
class FailureReport(models.Model):

    IMPACT = (
        ('s', 'La seguridad personal'),
        ('m', 'El medio ambiente'),
        ('i', 'Integridad del equipo/sistema'),
        ('o', 'El desarrollo normal de las operaciones'),
    )

    reporter = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    report = models.CharField(max_length=100, null=True, blank=True)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, null=True, blank=True)
    moment = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    causas = models.TextField()
    suggest_repair = models.TextField(null=True, blank=True)
    critico = models.BooleanField()
    evidence = models.ImageField(upload_to=get_upload_path, null=True, blank=True)
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


# Model 12+1: Proyectos/operaciones para barcos
class Operation(models.Model):

    start = models.DateField()
    end = models.DateField()
    proyecto = models.CharField(max_length=100)
    requirements = models.TextField()
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, to_field='abbreviation')
    confirmado = models.BooleanField(default=False)

    def requirements_progress(self):
        total_requirements = self.requirement_set.count()
        if total_requirements == 0:
            return None
        approved_requirements = self.requirement_set.filter(approved=True).count()
        progress_percentage = (approved_requirements / total_requirements) * 100
        return int(progress_percentage)

    def __str__(self):
        return f"{self.proyecto}/{self.asset} ({self.start} - {self.start})"
    

# Model 14: Requerimientos para proyectos
class Requirement(models.Model):

    operation = models.ForeignKey(Operation, on_delete=models.CASCADE)
    text = models.TextField()
    approved = models.BooleanField(default=False)
    novedad = models.TextField(null=True, blank=True)
    responsable = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        permissions = [
            ('can_create_requirement', 'Can create requirement'),
            ('can_delete_requirement', 'Can delete requirement'),
        ]


# Model 15: Solicitudes de compra
class Solicitud(models.Model):

    DPTO = (
        ('m', 'Mantenimiento'),
        ('o', 'Operaciones'),
    )

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


# Model 16: Salidas de articulos de la empresa
class Salida(models.Model):

    destino = models.CharField(max_length=200)
    fecha = models.DateField(auto_now_add=True)
    motivo = models.TextField()
    propietario = models.CharField(max_length=100)
    responsable = models.CharField(max_length=100)
    recibe = models.CharField(max_length=100)
    vehiculo = models.CharField(max_length=100, null=True, blank=False)
    auth = models.BooleanField(default=False)
    sign_recibe = models.ImageField(upload_to=get_upload_path, null=True, blank=True)
    adicional = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.motivo} - {self.fecha}"
    
    class Meta:
        permissions = (
            ('can_approve_it', 'Aprobar salidas'),
            )
        ordering = ['-fecha']

@receiver(pre_save, sender=Solicitud)
def update_solicitud_dates(sender, instance, **kwargs):
    if instance.id is not None:
        old_instance = Solicitud.objects.get(id=instance.id)
        
        if not old_instance.approved and instance.approved:
            instance.approval_date = timezone.now()

        if not old_instance.num_sc and instance.num_sc:
            instance.sc_change_date = timezone.now()

        if not old_instance.num_sc and instance.cancel:
            instance.cancel_date = timezone.now()


# Model 17: Suministros (Inventario para barcos o bodegas, contenido de equipos o ...)
class Suministro(models.Model):

    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00')) 
    Solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, null=True, blank=True)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, null=True, blank=True, related_name='suministros')
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, null=True, blank=True, related_name='suministros')
    salida = models.ForeignKey(Salida, on_delete=models.CASCADE, null=True, blank=True, related_name='suministros')

    def __str__(self):
        return f"{self.cantidad} {self.item.presentacion} - {self.item} "


# Model 18: Registro de movimientos de suminsitros realizados en los barcos o bodegas locativas
class Transaction(models.Model):

    TIPO = (
        ('i', 'Ingreso'),
        ('c', 'Consumo'),
        ('t', 'Transferencia'),
        ('e', 'Ingreso externo'),
    )

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


# Model 19: Registro estimado de reportes de combustible
class DailyFuelConsumption(models.Model):
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='fuel_consumptions')
    fecha = models.DateField(default=timezone.now)
    com_estimado_motor = models.DecimalField(max_digits=1000, decimal_places=2, default=0)

    class Meta:
        unique_together = ('equipo', 'fecha')
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.equipo}: {self.com_estimado_motor} - {self.fecha}'


# Model 20: Registros de pruebas megger (Pruebas de aislamiento)
class Megger(models.Model):

    ot = models.ForeignKey(Ot, on_delete=models.CASCADE)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE)
    date_report = models.DateField(auto_now_add=True, null=True, blank=True)

    estator_pi_1min_l1_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"Prueba #{self.id}/{self.equipo}"


# Model 20.1: 
class Estator(models.Model):

    megger = models.OneToOneField(Megger, on_delete=models.CASCADE)
    pi_1min_l1_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)#
    pi_1min_l2_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_1min_l3_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_1min_l1_l2 = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_1min_l2_l3 = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_1min_l3_l1 = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    pi_10min_l1_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_10min_l2_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_10min_l3_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_10min_l1_l2 = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_10min_l2_l3 = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_10min_l3_l1 = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    pi_obs_l1_tierra = models.TextField(null=True, blank=True)
    pi_obs_l2_tierra = models.TextField(null=True, blank=True)
    pi_obs_l3_tierra = models.TextField(null=True, blank=True)
    pi_obs_l1_l2 = models.TextField(null=True, blank=True)
    pi_obs_l2_l3 = models.TextField(null=True, blank=True)
    pi_obs_l3_l1 = models.TextField(null=True, blank=True)

    pf_1min_l1_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_1min_l2_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_1min_l3_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_1min_l1_l2 = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_1min_l2_l3 = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_1min_l3_l1 = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    pf_10min_l1_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_10min_l2_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_10min_l3_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_10min_l1_l2 = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_10min_l2_l3 = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_10min_l3_l1 = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    pf_obs_l1_tierra = models.TextField(null=True, blank=True)
    pf_obs_l2_tierra = models.TextField(null=True, blank=True)
    pf_obs_l3_tierra = models.TextField(null=True, blank=True)
    pf_obs_l1_l2 = models.TextField(null=True, blank=True)
    pf_obs_l2_l3 = models.TextField(null=True, blank=True)
    pf_obs_l3_l1 = models.TextField(null=True, blank=True)


# Model 20.2
class Excitatriz(models.Model):

    megger = models.OneToOneField(Megger, on_delete=models.CASCADE)
    pi_1min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_10min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_obs_l_tierra = models.TextField(null=True, blank=True)

    pf_1min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_10min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_obs_l_tierra = models.TextField(null=True, blank=True)


# Model 20.3
class RotorMain(models.Model):

    megger = models.OneToOneField(Megger, on_delete=models.CASCADE)
    pi_1min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_10min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_obs_l_tierra = models.TextField(null=True, blank=True)

    pf_1min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_10min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_obs_l_tierra = models.TextField(null=True, blank=True)


# Model 20.4
class RotorAux(models.Model):

    megger = models.OneToOneField(Megger, on_delete=models.CASCADE)
    pi_1min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_10min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_obs_l_tierra = models.TextField(null=True, blank=True)

    pf_1min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_10min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_obs_l_tierra = models.TextField(null=True, blank=True)


# Model 20.5
class RodamientosEscudos(models.Model):

    megger = models.OneToOneField(Megger, on_delete=models.CASCADE)
    rodamientoas = models.TextField(null=True, blank=True)
    rodamientobs = models.TextField(null=True, blank=True)
    escudoas = models.TextField(null=True, blank=True)
    escudobs = models.TextField(null=True, blank=True)


# Model 22: Imagenes
class Image(models.Model):

    image = models.ImageField(upload_to=get_upload_path)
    failure = models.ForeignKey(FailureReport, related_name='images', on_delete=models.CASCADE, null=True, blank=True)
    equipo = models.ForeignKey(Equipo, related_name='images', on_delete=models.CASCADE, null=True, blank=True)
    task = models.ForeignKey(Task, related_name='images', on_delete=models.CASCADE, null=True, blank=True)
    solicitud = models.ForeignKey(Solicitud, related_name='images', on_delete=models.CASCADE, null=True, blank=True)
    salida= models.ForeignKey(Salida, related_name='images', on_delete=models.CASCADE, null=True, blank=True)
    preoperacional = models.ForeignKey(Preoperacional, related_name='images', on_delete=models.CASCADE, null=True, blank=True)
    preoperacionaldiario = models.ForeignKey(PreoperacionalDiario, related_name='images', on_delete=models.CASCADE, null=True, blank=True)
    darbaja = models.ForeignKey(DarBaja, related_name='images', on_delete=models.CASCADE, null=True, blank=True)
    requirements = models.ForeignKey(Requirement, related_name='images', on_delete=models.CASCADE, null=True, blank=True)


# Model 24: Documentos
class Document(models.Model):

    asset = models.ForeignKey(Asset, related_name='documents', on_delete=models.CASCADE, null=True, blank=True)
    ot = models.ForeignKey(Ot, related_name='documents', on_delete=models.CASCADE, null=True, blank=True)
    equipo = models.ForeignKey(Equipo, related_name='documents', on_delete=models.CASCADE, null=True, blank=True)
    file = models.FileField(upload_to=get_upload_pdfs)
    description = models.CharField(max_length=200)


