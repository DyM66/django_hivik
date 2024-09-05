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
from django.contrib.humanize.templatetags.humanize import intcomma


def get_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"media/{datetime.now():%Y%m%d%H%M%S}-{uuid.uuid4()}.{ext}"
    return filename


def get_upload_pdfs(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"pdfs/{uuid.uuid4()}.{ext}"
    return filename


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    cargo = models.CharField(max_length=100, null=True, blank=True)
    firma = models.ImageField(upload_to=get_upload_path, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    instance.profile.save()


class Item(models.Model):

    SECCION = (
        ('c', 'Consumibles'),
        ('h', 'Herramientas y equipos'),
        ('r', 'Repuestos'),
    )

    name = models.CharField(max_length=50)
    reference = models.CharField(max_length=100, null=True, blank=True)
    imagen = models.ImageField(upload_to=get_upload_path, null=True, blank=True)
    presentacion = models.CharField(max_length=10)
    code = models.CharField(max_length=50, null=True, blank=True)
    seccion = models.CharField(max_length=1, choices=SECCION, default='c')

    def __str__(self):
        return f"{self.name} {self.reference}"

    class Meta:
        ordering = ['name', 'reference']
        

class Asset(models.Model):

    AREA = (
        ('a', 'Motonave'),
        ('b', 'Buceo'),
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
    bandera = models.CharField(default='Colombia', max_length=50, null=True, blank=True)
    eslora = models.DecimalField(default=0, max_digits=8, decimal_places=2, null=True, blank=True)
    manga = models.DecimalField(default=0, max_digits=8, decimal_places=2, null=True, blank=True)
    puntal = models.DecimalField(default=0, max_digits=8, decimal_places=2, null=True, blank=True)
    calado_maximo = models.DecimalField(default=0, max_digits=8, decimal_places=2, null=True, blank=True)
    deadweight = models.IntegerField(default=0, null=True, blank=True)
    arqueo_bruto = models.IntegerField(default=0, null=True, blank=True)
    arqueo_neto = models.IntegerField(default=0, null=True, blank=True)

    def check_ruta_status(self, frecuency, location=None):
        if location:
            rutas = self.system_set.filter(rutas__frecuency=frecuency, rutas__system__location=location)
        else:
            rutas = self.system_set.filter(rutas__frecuency=frecuency)
        
        if not rutas.exists():
            return "---"
        all_on_time = True
        for system in rutas:
            for ruta in system.rutas.filter(frecuency=frecuency):
                if ruta.next_date < date.today():
                    all_on_time = False
                    break
            if not all_on_time:
                break
        return "Ok" if all_on_time else "Requiere" 


    def ind_mtto(self):
        rutas = self.system_set.all().annotate(total_rutas=Count('rutas')).exclude(total_rutas=0)
        if not rutas:
            return "---"

        total_rutas = 0
        total_on_time = 0

        for system in rutas:
            for ruta in system.rutas.all():
                total_rutas += 1
                if ruta.next_date > date.today():
                    if not ruta.ot:
                        total_on_time += 0.4
                    elif ruta.ot.state=='x':
                        total_on_time += 0.5
                    elif ruta.ot.state=='f':
                        total_on_time += 1

        if total_rutas == 0:
            return "---"  
        maintenance_percentage = (total_on_time / total_rutas) * 100
        return f'{round(maintenance_percentage, 2)}%'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('got:asset-detail', args=[str(self.abbreviation)])

    class Meta:
        permissions = (('can_see_completely', 'Access to completely info'),)
        ordering = ['area', 'name']


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

    def __str__(self):
        return '%s/ %s' % (self.asset, self.name)

    def get_absolute_url(self):
        return reverse('got:sys-detail', args=[self.id])

    class Meta:
        ordering = ['asset__name', 'group']
    
    @property
    def maintenance_percentage(self):
        rutas = self.rutas.all()
        if not rutas:
            return 0

        total_value = 0

        for ruta in rutas:
            if ruta.maintenance_status == 'c':
                total_value += 1
            elif ruta.maintenance_status == 'p':
                total_value += 0.2
            elif ruta.maintenance_status == 'e' and ruta.next_date > date.today():
                total_value += 0.3
            elif ruta.maintenance_status == 'x':
                total_value += 0.5

        max_possible_value = len(rutas)
        if max_possible_value == 0:
            return "---"

        return round((total_value / max_possible_value) * 100, 2)


class Equipo(models.Model):

    TIPO = (
        ('a', 'Climatización'),
        ('b', 'Bomba'),
        ('c', 'Compresor'),
        ('d', 'Grúa'),
        ('e', 'Motor eléctrico'),
        ('g', 'Generador'),
        ('h', 'Cilindro hidráulico'),
        ('i', 'Instrumentos y herramientas'),
        ('k', 'Tanque de almacenamiento'),
        ('m', 'Comunicación'),
        ('n', 'Navegación'),
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
    subsystem = models.CharField(max_length=100, null=True, blank=True)

    'Motores'
    potencia  = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    'Motores de combustion'
    initial_hours = models.IntegerField(default=0)
    horometro = models.IntegerField(default=0, null=True, blank=True)
    prom_hours = models.IntegerField(default=0, null=True, blank=True)

    'Motores eléctricos'
    # rod_as = models.CharField(max_length=100, null=True, blank=True)
    # rod_bs = models.CharField(max_length=100, null=True, blank=True)

    'Tanques'
    tipo_almacenamiento = models.CharField(max_length=100, null=True, blank=True)
    volumen = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    manual_pdf = models.FileField(upload_to=get_upload_pdfs, null=True, blank=True)

    def volumen_format(self):
        if self.volumen is not None:
            return f'{self.volumen:,.2f}'
        return None
    
    @property
    def consumo_promedio_por_hora(self):
        if self.tipo != 'r':
            return None

        # Tomar los últimos 30 registros de consumo de combustible
        consumos = self.fuel_consumptions.order_by('-fecha')[:30]
        total_consumo = consumos.aggregate(Sum('com_estimado_motor'))['com_estimado_motor__sum'] or 0

        # Tomar la suma de las horas correspondientes a esos días
        fechas_consumo = consumos.values_list('fecha', flat=True)
        total_horas = HistoryHour.objects.filter(component=self, report_date__in=fechas_consumo).aggregate(Sum('hour'))['hour__sum'] or 0

        if total_horas > 0:
            return total_consumo / total_horas
        return None

    def calculate_horometro(self):
        total_hours = self.hours.aggregate(total=Sum('hour'))['total'] or 0
        return total_hours + self.initial_hours
    
    def last_hour_report_date(self):
        last_report = self.hours.order_by('-report_date').first()
        return last_report.report_date if last_report else None
    
    @property
    def ruta_proxima(self):
        rutas = self.equipos.exclude(nivel=1)
        future_rutas = [ruta for ruta in rutas if ruta.next_date and ruta.next_date > date.today()]

        if not future_rutas:
            return None 

        next_ruta = min(future_rutas, key=lambda ruta: ruta.next_date)

        return next_ruta

    def __str__(self):
        return f"{self.system.asset} - {self.name}"

    class Meta:
        ordering = ['name', 'code']

    def get_absolute_url(self):
        return reverse('got:sys-detail-view', args=[self.system.id, self.code])


class Location(models.Model):

    name = models.CharField(max_length=50)
    direccion = models.CharField(max_length=100)
    contact = models.CharField(max_length=50, null=True, blank=True)
    num_contact = models.CharField(max_length=50, null=True, blank=True)
    latitude = models.DecimalField(max_digits=20, decimal_places=20, null=True, blank=True)
    longitude = models.DecimalField(max_digits=20, decimal_places=20, null=True, blank=True)

    def __str__(self):
        return self.name


class HistoryHour(models.Model):

    report_date = models.DateField()
    hour = models.DecimalField(max_digits=10, decimal_places=2)
    reporter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    component = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='hours')

    def __str__(self):
        return '%s: %s - %s (%s) /%s' % (self.report_date, self.component, self.hour, self.reporter, self.component.system.asset)

    class Meta:
        ordering = ['-report_date']
        unique_together = ('component', 'report_date')


class Ot(models.Model):

    STATUS = (
        ('a', 'Abierto'),
        ('x', 'En ejecución'),
        ('f', 'Finalizado'),
        ('c', 'Cancelado'),
    )

    TIPO_MTTO = (
        ('p', 'Preventivo'),
        ('c', 'Correctivo'),
        ('m', 'Modificativo'),
    )

    creation_date = models.DateField(auto_now_add=True)
    num_ot = models.AutoField(primary_key=True)
    system = models.ForeignKey(System, on_delete=models.CASCADE)
    description = models.TextField()

    super = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    supervisor = models.CharField(max_length=100, null=True, blank=True)

    state = models.CharField(choices=STATUS, default='x', max_length=1)
    tipo_mtto = models.CharField(choices=TIPO_MTTO, max_length=1)

    sign_supervision = models.ImageField(upload_to=get_upload_path, null=True, blank=True)

    @property
    def formatted_presupuesto(self):
        return f"${number_format(self.presupuesto, decimal_pos=2, use_l10n=True, force_grouping=True)} COP"


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


class Ruta(models.Model):

    CONTROL = (
        ('d', 'Días'),
        ('h', 'Horas'),
        ('k', 'Kilómetros')
    )

    NIVEL = (
        (1, 'Nivel 1 - Operadores'),
        (2, 'Nivel 2 - Operador Técnico'),
        (3, 'Nivel 3 - Proveedor especializado'),
        (4, 'Nivel 4 - Fabricante')
    )

    code = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    control = models.CharField(choices=CONTROL, max_length=1)
    frecuency = models.IntegerField()
    intervention_date = models.DateField()

    nivel = models.IntegerField(choices=NIVEL, default=1)

    astillero = models.CharField(max_length=50, null=True, blank=True)

    ot = models.ForeignKey(Ot, on_delete=models.SET_NULL, null=True, blank=True)
    system = models.ForeignKey(System, on_delete=models.CASCADE, related_name='rutas')
    equipo = models.ForeignKey(Equipo, on_delete=models.SET_NULL, null=True, blank=True, related_name='equipos')
    dependencia = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='dependiente')


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


class Task(models.Model):

    ot = models.ForeignKey(Ot, on_delete=models.CASCADE, null=True, blank=True)
    ruta = models.ForeignKey(Ruta, on_delete=models.CASCADE, null=True, blank=True)
    responsible = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField()
    procedimiento = models.TextField(default="", blank=True, null=True)
    hse = models.TextField(default="", blank=True, null=True)
    news = models.TextField(blank=True, null=True)
    
    evidence = models.ImageField(upload_to=get_upload_path, null=True, blank=True)
    
    priority = models.IntegerField(default=0, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    men_time = models.IntegerField(default=0)
    finished = models.BooleanField()

    def __str__(self):
        return self.description

    def get_absolute_url(self):
        return reverse('got:task-detail', args=[str(self.id)])

    @property
    def is_overdue(self):
        overdue_date = self.start_date + timedelta(days=self.men_time)
        return self.start_date and date.today() > overdue_date

    @property
    def final_date(self):
        return self.start_date + timedelta(days=self.men_time)
 
    class Meta:
        permissions = (
            ('can_reschedule_task', 'Reprogramar actividades'),
            ('can_modify_any_task', 'Can modify any task'),
            )
        ordering = ['-priority', '-start_date'] 


class FailureReport(models.Model):

    IMPACT = (
        ('s', 'La seguridad personal'),
        ('m', 'El medio ambiente'),
        ('i', 'Integridad del equipo/sistema'),
        ('o', 'El desarrollo normal de las operaciones'),
    )

    reporter = models.ForeignKey(User, on_delete=models.CASCADE)
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


class Operation(models.Model):

    start = models.DateField()
    end = models.DateField()
    proyecto = models.CharField(max_length=100)
    requirements = models.TextField()
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, to_field='abbreviation')
    confirmado = models.BooleanField(default=False, null=True, blank=True)

    def __str__(self):
        return f"{self.proyecto}/{self.asset} ({self.start} - {self.start})"


class Solicitud(models.Model):

    creation_date = models.DateTimeField(auto_now_add=True)
    solicitante = models.ForeignKey(User, on_delete=models.CASCADE)
    ot = models.ForeignKey(Ot, on_delete=models.CASCADE, null=True, blank=True)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, null=True, blank=True)
    suministros = models.TextField()
    num_sc = models.TextField(null=True, blank=True)

    approved_by = models.CharField(max_length=100, null=True, blank=True, default='Jader Aguilar')
    approved = models.BooleanField(default=False)

    approval_date = models.DateTimeField(null=True, blank=True) 
    sc_change_date = models.DateTimeField(null=True, blank=True)

    cancel_date = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.TextField(null=True, blank=True)
    cancel = models.BooleanField(default=False)

    # proveedor = models.CharField(max_length=100, null=True, blank=True)
    # inversion = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)], default=0, verbose_name="Inversión (COP)")

    def __str__(self):
        return f"Suministros para {self.asset}/{self.ot}"
    
    class Meta:
        permissions = (
            ('can_approve', 'Aprobar solicitudes'),
            ('can_cancel', 'Puede cancelar'),
            )
        ordering = ['-creation_date']


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


class Suministro(models.Model):

    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    Solicitud = models.ForeignKey(Solicitud, on_delete=models.CASCADE, null=True, blank=True)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, null=True, blank=True, related_name='suministros')
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, null=True, blank=True, related_name='suministros')
    salida = models.ForeignKey(Salida, on_delete=models.CASCADE, null=True, blank=True, related_name='suministros')

    def __str__(self):
        return f"{self.cantidad} {self.item.presentacion} - {self.item} "


class TransaccionSuministro(models.Model):
    suministro = models.ForeignKey(Suministro, on_delete=models.CASCADE, related_name='transacciones')
    cantidad_ingresada = models.IntegerField(default=0, help_text="Cantidad que se añade al inventario")
    cantidad_consumida = models.IntegerField(default=0, help_text="Cantidad que se consume del inventario")
    fecha = models.DateField()
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.suministro.item.name}: +{self.cantidad_ingresada}/-{self.cantidad_consumida} el {self.fecha.strftime('%Y-%m-%d')}"

    class Meta:
        unique_together = ('suministro', 'fecha')


class DailyFuelConsumption(models.Model):
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='fuel_consumptions')
    fecha = models.DateField(default=timezone.now)
    com_estimado_motor = models.DecimalField(max_digits=1000, decimal_places=2, default=0)

    class Meta:
        unique_together = ('equipo', 'fecha')
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.equipo}: {self.com_estimado_motor} - {self.fecha}'


class Megger(models.Model):

    ot = models.ForeignKey(Ot, on_delete=models.CASCADE)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE)
    date_report = models.DateField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"Prueba #{self.id}/{self.equipo}"


class Estator(models.Model):

    megger = models.OneToOneField(Megger, on_delete=models.CASCADE)
    pi_1min_l1_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
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


class Excitatriz(models.Model):

    megger = models.OneToOneField(Megger, on_delete=models.CASCADE)
    pi_1min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_10min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_obs_l_tierra = models.TextField(null=True, blank=True)

    pf_1min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_10min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_obs_l_tierra = models.TextField(null=True, blank=True)


class RotorMain(models.Model):

    megger = models.OneToOneField(Megger, on_delete=models.CASCADE)
    pi_1min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_10min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_obs_l_tierra = models.TextField(null=True, blank=True)

    pf_1min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_10min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_obs_l_tierra = models.TextField(null=True, blank=True)


class RotorAux(models.Model):

    megger = models.OneToOneField(Megger, on_delete=models.CASCADE)
    pi_1min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_10min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_obs_l_tierra = models.TextField(null=True, blank=True)

    pf_1min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_10min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_obs_l_tierra = models.TextField(null=True, blank=True)


class RodamientosEscudos(models.Model):

    megger = models.OneToOneField(Megger, on_delete=models.CASCADE)
    rodamientoas = models.TextField(null=True, blank=True)
    rodamientobs = models.TextField(null=True, blank=True)
    escudoas = models.TextField(null=True, blank=True)
    escudobs = models.TextField(null=True, blank=True)


class Preoperacional(models.Model):

    RUTA = (
        ('u', 'Urbana'),
        ('r', 'Rural'),
        ('m', 'Mixta (Urbana y Rural)')
    )

    AUTORIZADO = (
        ('a', 'Alejandro Angel/ Deliana Lacayo/ Jenny Castillo - Dpto. abasteciiento y logistica'),
        ('b', 'Juan Pablo Llanos - Residente Santa Marta'),
        ('c', 'Jose Jurado/ Julieth Ximena - Residente Tumaco'),
        ('d', 'Issis Alvarez - Directora Administrativa'),
        ('e', 'Jennifer Padilla - Gerente administrativa'),
        ('f', 'German Locarno - Gerente de operaciones'),
        ('g', 'Alexander Davey - Gerente de mantenimiento'),
        ('h', 'Carlos Cortés - Subgerente'),
        ('i', 'Federico Payan - Gerente Financiero'),
        ('j', 'Diego Lievano - Jefe de buceo'),
        ('k', 'Klaus Bartel - Gerente General'),
    )

    fecha = models.DateField(auto_now_add=True)
    reporter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    nombre_no_registrado = models.CharField(max_length=100, null=True, blank=True)
    cedula = models.CharField(max_length=20)
    kilometraje = models.IntegerField()
    motivo = models.TextField()
    salida = models.CharField(max_length=150)
    destino = models.CharField(max_length=150)
    tipo_ruta = models.CharField(max_length=1, choices=RUTA)
    autorizado = models.CharField(max_length=1, choices=AUTORIZADO)
    vehiculo = models.ForeignKey(Equipo, on_delete=models.CASCADE)
    observaciones = models.TextField(null=True, blank=True)
    horas_trabajo = models.BooleanField()
    medicamentos = models.BooleanField()
    molestias = models.BooleanField()
    enfermo = models.BooleanField()
    condiciones = models.BooleanField()
    agua = models.BooleanField()
    dormido = models.BooleanField()
    control = models.BooleanField()
    sueño = models.BooleanField()   
    radio_aire = models.BooleanField()

    class Meta:
        ordering = ['-fecha']


class PreoperacionalDiario(models.Model):

    COMBUSTUBLE = (
        ('f', 'Lleno'),
        ('a', '3/4'),
        ('b', '1/2'),
        ('c', '1/4'),
        ('d', '1/8'),
    )

    LEVEL = (
        ('b', 'Bajo'),
        ('m', 'Medio'),
        ('l', 'Lleno'),
    )

    ESTADO = (
        ('b', 'Bueno'),
        ('r', 'Regular'),
        ('m', 'Malo'),
    )

    FISICO = (
        ('l', 'Raya leve'),
        ('p', 'Rayón profundo'),
        ('f', 'Golpe fuerte'),
        ('b', 'Bueno'),
    )

    PLACA = (
        ('a', 'Buena'),
        ('b', 'Descolorida'),
        ('c', 'Rota/Partida'), 
        ('m', 'Mala'), 
    )

    vehiculo = models.ForeignKey(Equipo, on_delete=models.CASCADE)
    fecha = models.DateField(auto_now_add=True)
    reporter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    nombre_no_registrado = models.CharField(max_length=100, null=True, blank=True)
    kilometraje = models.IntegerField()
    combustible_level = models.CharField(max_length=1, default='f', choices=COMBUSTUBLE)
    aceite_level = models.CharField(max_length=1, default='l', choices=LEVEL)
    refrigerante_level = models.CharField(max_length=1, default='l', choices=LEVEL)
    hidraulic_level = models.CharField(max_length=1, default='l', choices=LEVEL)
    liq_frenos_level = models.CharField(max_length=1, default='l', choices=LEVEL)
    poleas = models.CharField(max_length=1, default='b', choices=ESTADO)
    correas = models.CharField(max_length=1, default='b', choices=ESTADO)
    mangueras = models.CharField(max_length=1, default='b', choices=ESTADO)
    acoples = models.CharField(max_length=1, default='b', choices=ESTADO)
    tanques = models.CharField(max_length=1, default='b', choices=ESTADO)
    radiador = models.CharField(max_length=1, default='b', choices=ESTADO)
    terminales = models.CharField(max_length=1, default='b', choices=ESTADO)
    bujes = models.CharField(max_length=1, default='b', choices=ESTADO)
    rotulas = models.CharField(max_length=1, default='b', choices=ESTADO)
    ejes = models.CharField(max_length=1, default='b', choices=ESTADO)
    cruceta = models.CharField(max_length=1, default='b', choices=ESTADO)
    puertas = models.CharField(max_length=1, default='b', choices=ESTADO)
    chapas = models.CharField(max_length=1, default='b', choices=ESTADO)
    manijas = models.CharField(max_length=1, default='b', choices=ESTADO)
    elevavidrios = models.CharField(max_length=1, default='b', choices=ESTADO)
    lunas = models.CharField(max_length=1, default='b', choices=ESTADO)
    espejos = models.CharField(max_length=1, default='b', choices=ESTADO)
    vidrio_panoramico = models.CharField(max_length=1, default='b', choices=ESTADO)
    asiento = models.CharField(max_length=1, default='b', choices=ESTADO)
    apoyacabezas = models.CharField(max_length=1, default='b', choices=ESTADO)
    cinturon = models.CharField(max_length=1, default='b', choices=ESTADO)
    aire = models.CharField(max_length=1, default='b', choices=ESTADO)
    caja_cambios = models.CharField(max_length=1, default='b', choices=ESTADO)
    direccion = models.CharField(max_length=1, default='b', choices=ESTADO)
    bateria = models.CharField(max_length=1, default='b', choices=ESTADO)
    luces_altas = models.CharField(max_length=1, default='b', choices=ESTADO)
    luces_medias = models.CharField(max_length=1, default='b', choices=ESTADO)
    luces_direccionales = models.CharField(max_length=1, default='b', choices=ESTADO)
    cocuyos = models.CharField(max_length=1, default='b', choices=ESTADO)
    luz_placa = models.CharField(max_length=1, default='b', choices=ESTADO)
    luz_interna = models.CharField(max_length=1, default='b', choices=ESTADO)
    pito = models.CharField(max_length=1, default='b', choices=ESTADO)
    alarma_retroceso = models.CharField(max_length=1, default='b', choices=ESTADO)
    arranque = models.CharField(max_length=1, default='b', choices=ESTADO)
    alternador = models.CharField(max_length=1, default='b', choices=ESTADO)
    rines = models.CharField(max_length=1, default='b', choices=ESTADO)
    tuercas = models.CharField(max_length=1, default='b', choices=ESTADO)
    esparragos = models.CharField(max_length=1, default='b', choices=ESTADO)
    freno_servicio = models.CharField(max_length=1, default='b', choices=ESTADO)
    freno_seguridad = models.CharField(max_length=1, default='b', choices=ESTADO)
    is_llanta_repuesto = models.BooleanField()
    llantas = models.CharField(max_length=1, default='b', choices=ESTADO)
    suspencion = models.CharField(max_length=1, default='b', choices=ESTADO)
    capo = models.CharField(max_length=1, default='b', choices=FISICO)
    persiana = models.CharField(max_length=1, default='b', choices=FISICO)
    bumper_delantero = models.CharField(max_length=1, default='b', choices=FISICO)
    panoramico = models.CharField(max_length=1, default='b', choices=FISICO)
    guardafango = models.CharField(max_length=1, default='b', choices=FISICO)
    puerta = models.CharField(max_length=1, default='b', choices=FISICO)
    parales = models.CharField(max_length=1, default='b', choices=FISICO)
    stop = models.CharField(max_length=1, default='b', choices=FISICO)
    bumper_trasero = models.CharField(max_length=1, default='b', choices=FISICO)
    vidrio_panoramico_trasero = models.CharField(max_length=1, default='b', choices=FISICO)
    placa_delantera = models.CharField(max_length=1, default='a', choices=PLACA)
    placa_trasera = models.CharField(max_length=1, default='a', choices=PLACA)
    aseo_externo = models.BooleanField()
    aseo_interno = models.BooleanField()
    kit_carreteras = models.BooleanField()
    kit_herramientas = models.BooleanField()
    kit_botiquin = models.BooleanField()
    chaleco_reflectivo = models.BooleanField()
    aprobado = models.BooleanField(default=True)
    observaciones = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha']


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
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE)
    activo = models.CharField(max_length=100)
    motivo = models.CharField(max_length=1, choices=MOTIVO)
    observaciones = models.TextField()
    disposicion = models.TextField()
    firma_responsable = models.ImageField(upload_to=get_upload_path)
    firma_autorizado = models.ImageField(upload_to=get_upload_path)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.activo}/{self.equipo} - {self.fecha}"
    

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


class Document(models.Model):

    asset = models.ForeignKey(Asset, related_name='documents', on_delete=models.CASCADE, null=True, blank=True)
    ot = models.ForeignKey(Ot, related_name='documents', on_delete=models.CASCADE, null=True, blank=True)
    equipo = models.ForeignKey(Equipo, related_name='documents', on_delete=models.CASCADE, null=True, blank=True)
    file = models.FileField(upload_to=get_upload_pdfs)
    description = models.CharField(max_length=200)

