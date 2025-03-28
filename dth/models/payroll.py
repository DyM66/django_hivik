# dth/models/payroll.py
from django.db import models
from decimal import Decimal
from django.contrib.auth.models import User
from got.paths import get_upload_path

RISK_CLASS_CHOICES = [('I', '0.522%'), ('II', '1.044%'), ('III', '2.436%'), ('IV', '4.350%'), ('V', '6.96%'),]


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    cargo = models.CharField(max_length=100, null=True, blank=True)
    firma = models.ImageField(upload_to=get_upload_path, null=True, blank=True)
    dpto = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'got_userprofile'

    def __str__(self):
        return f"{self.user.username}'s profile"


class Department(models.Model):
    """
    Representa un departamento dentro de la empresa.
    Cada departamento puede tener muchas personas asociadas (Nomina).
    """
    name = models.CharField(max_length=100, unique=True, help_text="Nombre del departamento.")

    def __str__(self):
        return self.name


class Nomina(models.Model):
    RISK_CLASS_CHOICES = [('I', '0.522%'), ('II', '1.044%'), ('III', '2.436%'), ('IV', '4.350%'), ('V', '6.96%'),]
    GENDER_CHOICES = [('h', 'Hombre'), ('m', 'Mujer'),]
    id_number = models.CharField(max_length=50, verbose_name="Número de documento", help_text="Identificación del empleado.")
    name = models.CharField(max_length=100, help_text="Nombre del empleado.")
    surname = models.CharField(max_length=100, help_text="Apellido del empleado.")
    position = models.CharField(max_length=100, help_text="Cargo o puesto.")
    position_id = models.ForeignKey('dth.Position', on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    salary = models.DecimalField(max_digits=18, decimal_places=2, help_text="Salario en COP.")
    admission = models.DateField(help_text="Fecha de ingreso del empleado. (Obligatoria)")
    expiration = models.DateField(blank=True, null=True, help_text="Fecha de expiración del contrato, si aplica.")
    risk_class = models.CharField(max_length=3, choices=RISK_CLASS_CHOICES, blank=True, null=True, help_text="Clase de riesgo laboral.")
    is_driver = models.BooleanField(default=False)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='h')
    photo = models.ImageField(upload_to=get_upload_path, blank=True, null=True, help_text="Fotografía del empleado.")

    @property
    def photo_url(self):
        """
        Retorna la URL de la foto si existe;
        en caso contrario, devuelve una imagen de silueta por defecto.
        """
        if self.photo:
            return self.photo.url  # Foto real en S3
        # Si no hay foto, escogemos por género (o una sola imagen si lo prefieres)
        if self.gender == 'female':
            return 'https://hivik.s3.us-east-2.amazonaws.com/static/ChatGPT+Image+28+mar+2025%2C+10_36_11.png'
        else:
            return 'https://hivik.s3.us-east-2.amazonaws.com/static/ChatGPT+Image+28+mar+2025%2C+11_04_23.png'

    def __str__(self):
        return f"{self.name} {self.surname} - {self.id_number} - {self.position}"
    

class NominaReport(models.Model):
    mes = models.PositiveSmallIntegerField(help_text="Mes (1-12).")
    anio = models.PositiveSmallIntegerField(help_text="Año.")
    nomina = models.ForeignKey('dth.Nomina', on_delete=models.CASCADE, related_name='reportes')
    current_salary = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text="Salario Actual")
    dv01 = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text="Sueldo básico.")
    dv25 = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text="Pago Vacaciones")
    dv03 = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text="Subsidio de transporte")
    dv103 = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text="Licencia de la familia")
    dv27 = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text="Intereses de cesantías año anterior.")
    dv30 = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text="Cesantías.")
    dx03 = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text="Pensión.")
    dx05 = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text="Solidaridad.")
    dx01 = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text="Retención en la fuente.")
    dx07 = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text="Exequias Lordoy.")
    dx12 = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text="Descuento pensión voluntaria.")
    dx63 = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text="Banco de Occidente.")
    dx64 = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text="Confenalco.")
    dx66 = models.DecimalField(max_digits=18, decimal_places=2, default=Decimal('0.00'), help_text="Préstamo empleado.")

    # ---------- Propiedades Dinámicas ----------
    @property
    def dias_sueldo_basico(self):
        """
        (dv01 / 30) * salary del registro de Nomina
        """
        if self.nomina.salary == 0:
            return Decimal('0.00')
        return (self.dv01 / Decimal('30.00')) * self.nomina.salary

    @property
    def dias_vacaciones(self):
        """
        (dv25 / 30) * salary del registro de Nomina
        """
        if self.nomina.salary == 0:
            return Decimal('0.00')
        return (self.dv25 / Decimal('30.00')) * self.nomina.salary

    @property
    def provision_vacaciones(self):
        """
        dv25 (Pago Vacaciones) * 4.17%
        """
        return self.dv25 * Decimal('0.0417')

    @property
    def prima_servicio(self):
        """
        (dv01 + dv25 + dv03) * 8.33%
        """
        subtotal = self.dv01 + self.dv25 + self.dv03
        return subtotal * Decimal('0.0833')

    @property
    def intereses_cesantias(self):
        """
        dv30 (Cesantías) * 1%
        """
        return self.dv30 * Decimal('0.01')

    @property
    def salud_aporte(self):
        """
        (dv01 + dv25) * 4%
        """
        subtotal = self.dv01 + self.dv25
        return subtotal * Decimal('0.04')

    @property
    def pension_aporte_empleador(self):
        """
        (dv01 + dv25) * 12%
        """
        subtotal = self.dv01 + self.dv25
        return subtotal * Decimal('0.12')

    @property
    def arl_aporte(self):
        if not self.nomina.risk_class:
            return Decimal('0')
        try:
            value = Decimal(self.nomina.get_risk_class_display().replace('%', '').strip())
            rc = value / Decimal('100')
        except Exception:
            rc = Decimal('0')
        return self.dv01 * rc

    @property
    def caja_compensacion_aporte(self):
        """
        (dv01 + dv25) * 4%
        """
        subtotal = self.dv01 + self.dv25
        return subtotal * Decimal('0.04')

    @property
    def neto_a_pagar(self):
        """
        neto_a_pagar = (dv01 + dv25 + dv03 + dv27)
                       - [salud_aporte + dx03 + dx05 + dx01 + dx07 + dx12 + dx63 + dx64 + dx66]
        """
        # Lo que se suma:
        ingreso_bruto = self.dv01 + self.dv25 + self.dv03 + self.dv27

        # Restas (aportes y descuentos)
        descuentos = (
            self.salud_aporte +
            self.dx03 +    # Pensión
            self.dx05 +    # Solidaridad
            self.dx01 +    # Retención en la fuente
            self.dx07 +    # Exequias Lordoy
            self.dx12 +    # Descuento pensión voluntaria
            self.dx63 +    # Banco de Occidente
            self.dx64 +    # Confenalco
            self.dx66      # Préstamo empleado
        )

        return ingreso_bruto - descuentos

    def __str__(self):
        return f"NominaReport {self.mes}/{self.anio} - {self.nomina}"
