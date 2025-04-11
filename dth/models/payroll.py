# dth/models/payroll.py
from django.db import models
from decimal import Decimal
from django.contrib.auth.models import User
from got.paths import get_upload_path
from datetime import date

RISK_CLASS_CHOICES = [
        ('I', '0.522%'),
        ('II', '1.044%'),
        ('III', '2.436%'),
        ('IV', '4.350%'),
        ('V', '6.96%'),
    ]

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    cargo = models.CharField(max_length=100, null=True, blank=True)
    firma = models.ImageField(upload_to=get_upload_path, null=True, blank=True)
    VIEW_CHOICES = [('c', 'Tarjetas'), ('t', 'Tabla')]
    payroll_view_mode = models.CharField(max_length=1, choices=VIEW_CHOICES, default='c')

    class Meta:
        db_table = 'got_userprofile'

    def __str__(self):
        return f"{self.user.username}'s profile"


class Nomina(models.Model):
    GENDER_CHOICES = [('h', 'Hombre'), ('m', 'Mujer'),]
    EMPLOYMENT_STATUS_CHOICES = [('a', 'Activo'), ('r', 'Retirado'), ('l', 'Licencia'), ('s', 'Suspendido'), ('i', 'Incapacitado'),]

    id_number = models.CharField(max_length=50, verbose_name="Número de documento", help_text="Identificación del empleado.")
    name = models.CharField(max_length=100, help_text="Nombres")
    surname = models.CharField(max_length=100, help_text="Apellidos")
    position_id = models.ForeignKey('dth.Position', on_delete=models.CASCADE, related_name='employees')
    employment_status = models.CharField(max_length=1, choices=EMPLOYMENT_STATUS_CHOICES, default='a', help_text="Estado actual del empleado en la empresa.")

    is_driver = models.BooleanField(default=False)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='h')
    photo = models.ImageField(upload_to=get_upload_path, blank=True, null=True, help_text="Fotografía del empleado.")
    email = models.EmailField(blank=True, null=True, help_text="Correo electrónico del empleado.")
    phone = models.CharField(max_length=50, blank=True, null=True, help_text="Teléfono de contacto.")

    @property
    def photo_url(self):
        """
        Retorna la URL de la foto si existe;
        en caso contrario, devuelve una imagen de silueta por defecto.
        """
        if self.photo:
            return self.photo.url  # Foto real en S3
        # Si no hay foto, escogemos por género (o una sola imagen si lo prefieres)csratch
        if self.gender == 'm':
            return 'https://hivik.s3.us-east-2.amazonaws.com/static/img+generic+female.png'
        else:
            return 'https://hivik.s3.us-east-2.amazonaws.com/static/ChatGPT+Image+28+mar+2025%2C+11_04_23.png'

    def __str__(self):
        return f"{self.name} {self.surname} - {self.id_number} - {self.position_id.name}"
    

class PayrollDetails(models.Model):
    nomina = models.OneToOneField(Nomina, on_delete=models.CASCADE, related_name='details', primary_key=True)
    RISK_CLASS_CHOICES = [('I', '0.522%'), ('II', '1.044%'), ('III', '2.436%'), ('IV', '4.350%'), ('V', '6.96%'),]
    
    
    EDUCATION_LEVEL_CHOICES = [
        ('none', 'Ninguno'),
        ('sec_incompleta', 'Secundaria Incompleta'),
        ('sec_completa', 'Secundaria Completa'),
        ('tecnico', 'Técnico'),
        ('tecnologo', 'Tecnólogo'),
        ('pregrado', 'Profesional'),
        ('postgrado', 'Postgrado'),
    ]
    RH_CHOICES = [
        ('O+', 'O+'), ('O-', 'O-'),
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
    ]
    MARITAL_STATUS_CHOICES = [
        ('soltero', 'Soltero(a)'),
        ('casado', 'Casado(a)'),
        ('unionlibre', 'Unión Libre'),
        ('viudo', 'Viudo(a)'),
        ('divorciado', 'Divorciado(a)'),
    ]
    CRITICITY_CHOICES = [
        ('bajo', 'Bajo'),
        ('medio', 'Medio'),
        ('alto', 'Alto'),
    ]
    SALARY_TYPE_CHOICES = [
        ('ordinario', 'Ordinario'),
        ('variable', 'Variable'),
        ('integral', 'Integral'),
        ('especie', 'Especie'),
    ]
    SHIFT_CHOICES = [
        ('5x2', '5 x 2 (Lunes a Viernes)'),
        ('6x1', '6 x 1'),
        ('6x1_nav', '6 x 1 (Navegando 2 x 1)'),
        ('14x7', '14 x 7'),
        ('flexible', 'Jornada Flexible'),
        ('14x14', '14 x 14 (1 x 1)'),
    ]
    CONTRACT_TYPE_CHOICES = [
        ('indefinido', 'Indefinido'),
        ('definido', 'Término Definido'),
        ('aprendizaje', 'Aprendizaje'),
        ('obra', 'Obra/Labor'),
    ]
    RETIREMENT_CHOICES = [
        ('NA', 'N/A'),
        ('venc', 'Vencimiento del contrato'),
        ('volunt', 'Voluntario'),
        ('injusto', 'Injusta Causa'),
        ('justo', 'Justa Causa'),
        ('fin_obra', 'Finalización de la Obra'),
    ]
    CENTER_OF_WORK_CHOICES = [
        ('cartagena', 'Cartagena'),
        ('guyana', 'Guyana'),
    ]
    AFP_CHOICES = [
        ('proteccion', 'PROTECCIÓN'),
        ('porvenir', 'PORVENIR'),
        ('colpensiones', 'COLPENSIONES'),
    ]

    salary_type = models.CharField(max_length=10, choices=SALARY_TYPE_CHOICES, blank=True, null=True, help_text="Tipo de salario.")
    salary = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True, help_text="Salario en COP.")
    admission = models.DateField(help_text="Fecha de ingreso del empleado. (Obligatoria)", blank=True, null=True,)
    expiration = models.DateField(blank=True, null=True, help_text="Fecha de expiración del contrato, si aplica.")
    risk_class = models.CharField(max_length=3, choices=RISK_CLASS_CHOICES, blank=True, null=True, help_text="Clase de riesgo laboral.")

    birth_date = models.DateField(blank=True, null=True, help_text="Fecha de nacimiento.")
    place_of_birth = models.CharField(max_length=100, blank=True, null=True, help_text="Lugar de nacimiento (ciudad/municipio).")
    doc_expedition_date = models.DateField(blank=True, null=True, help_text="Fecha de expedición del documento de identidad.")
    doc_expedition_department = models.CharField(max_length=100, blank=True, null=True, help_text="Departamento expedición.")
    doc_expedition_municipality = models.CharField(max_length=100, blank=True, null=True, help_text="Municipio expedición.")

    education_level = models.CharField(max_length=20, choices=EDUCATION_LEVEL_CHOICES, blank=True, null=True, help_text="Nivel de escolaridad.")
    profession = models.CharField(max_length=200, blank=True, null=True, help_text="Profesión del empleado.")
    last_academic_institution = models.CharField(max_length=200, blank=True, null=True, help_text="Última institución de formación académica.")
    municipality_of_residence = models.CharField(max_length=100, blank=True, null=True, help_text="Municipio de residencia.")
    address = models.CharField(max_length=200, blank=True, null=True, help_text="Dirección de residencia.")
                               
    rh = models.CharField(max_length=3, choices=RH_CHOICES, blank=True, null=True, help_text="Grupo y factor RH.")  
    marital_status = models.CharField(max_length=12, choices=MARITAL_STATUS_CHOICES, blank=True, null=True, help_text="Estado civil.")
    
    eps = models.ForeignKey('dth.EPS', on_delete=models.SET_NULL, blank=True, null=True, help_text="EPS seleccionada")
    afp = models.CharField(max_length=15, choices=AFP_CHOICES, blank=True, null=True, help_text="Fondo de pensiones (entre 3 opciones).")
    caja_compensacion = models.CharField(max_length=100, blank=True, null=True, help_text="Caja de compensación.")
    retiro_concept = models.CharField(max_length=15, choices=RETIREMENT_CHOICES, blank=True, null=True, help_text="Concepto del retiro, si aplica.")
    center_of_work = models.CharField(max_length=20, choices=CENTER_OF_WORK_CHOICES, blank=True, null=True, help_text="Centro de trabajo actual.")
    contract_type = models.CharField(max_length=15, choices=CONTRACT_TYPE_CHOICES, blank=True, null=True, help_text="Tipo de contrato.")
    obra_description = models.TextField(blank=True, null=True, help_text="Descripción de la obra (si aplica).")
    months_term = models.PositiveIntegerField(blank=True, null=True, help_text="Término # de meses (si es contrato a término).")
    shift = models.CharField(max_length=15, choices=SHIFT_CHOICES, blank=True, null=True, help_text="Turno de trabajo.")
    criticity_level = models.CharField(max_length=6, choices=CRITICITY_CHOICES, blank=True, null=True, help_text="Nivel de criticidad.")
    bank_account = models.CharField(max_length=50, blank=True, null=True, help_text="Número de cuenta bancaria.")
    bank = models.CharField(max_length=100, blank=True, null=True, help_text="Banco asociado.")

    @property
    def age(self):
        """
        Calcula la edad a partir de birth_date, si aplica.
        """
        if self.birth_date:
            today = date.today()
            return (today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day)))
        return None

    @property
    def days_left_contract(self):
        """
        Si 'months_term' está definido y se quiere estimar
        la fecha de finalización respecto a la fecha de admisión de Nomina.
        Retorna días restantes (aprox) o None.
        """
        if self.nomina.admission and self.months_term:
            from datetime import timedelta
            start = self.nomina.admission
            # Aprox: months_term * 30 días
            end_date = start + timedelta(days=(self.months_term * 30))
            remaining = (end_date - date.today()).days
            return remaining if remaining > 0 else 0
        return None

    def __str__(self):
        # Muestra algo como: "Detalles de # Nomina: 123"
        return f"Detalles de {self.nomina.id_number}"


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
            value = Decimal(self.nomina.details.get_risk_class_display().replace('%', '').strip())
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
