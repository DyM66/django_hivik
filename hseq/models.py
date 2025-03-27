from django.db import models
from got.models import Asset
from django.contrib.auth.models import User
from got.paths import get_upload_path

# Create your models here.
class Permission(models.Model):
    issue_date = models.DateField(auto_now_add=True)
    registered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    area = models.ForeignKey(Asset, on_delete=models.CASCADE, null=True, blank=True)
    task = models.TextField('Descripción detallada de la actividad a desarrollar')
    tools = models.TextField('Maquinas, Herramientas y/o equipo a utilizar')
    is_chemical_substances = models.BooleanField(default=False)
    # q1 = 
    # Propiedad dimanica periodo de validez 7 dias

    ANSWERS_CHOICES = [('y', 'Sí'), ('n', 'No'), ('a', 'N/A'),]

    # Preguntas específicas
    capacitacion_especifica = models.CharField(
        max_length=2,
        choices=ANSWERS_CHOICES,
        help_text="¿Las personas que realizan el trabajo han recibido la formación, capacitación y entrenamiento específico en el trabajo a desarrollar e instrucciones de calidad, seguridad, salud y ambiente?"
    )

    reunion_preoperativa = models.CharField(
        max_length=2,
        choices=ANSWERS_CHOICES,
        help_text="¿Se realizó reunión preoperativa con los trabajadores sobre las tareas a seguir durante el desarrollo de los trabajos, y se ha notificado a los procesos o áreas afectados?"
    )

    analisis_riesgos = models.CharField(
        max_length=2,
        choices=ANSWERS_CHOICES,
        help_text="¿Se ha realizado un análisis previo de los riesgos existentes en el área y de las condiciones de seguridad, siendo conocido por todo el equipo de trabajo? (Adjuntar ATS)"
    )

    inspeccion_equipos = models.CharField(
        max_length=2,
        choices=ANSWERS_CHOICES,
        help_text="¿Los equipos a utilizar han sido inspeccionados, están en buenas condiciones y son apropiados para realizar el trabajo?"
    )

    presencia_hseq_supervisor = models.CharField(
        max_length=2,
        choices=ANSWERS_CHOICES,
        help_text="¿Se requiere presencia del proceso Gestión HSEQ, supervisor/jefe o un observador permanente durante la ejecución?"
    )

    epp_apropiados = models.CharField(
        max_length=2,
        choices=ANSWERS_CHOICES,
        help_text="¿Los empleados cuentan con todos los elementos de protección personal apropiados y en buenas condiciones?"
    )

    conocimiento_plan_emergencia = models.CharField(
        max_length=2,
        choices=ANSWERS_CHOICES,
        help_text="¿Todas las personas conocen el plan de emergencias, códigos de pitadas, rutas de evacuación, amenazas, puntos de encuentro y procedimientos en caso de emergencia?"
    )

    instalaciones_seguras = models.CharField(
        max_length=2,
        choices=ANSWERS_CHOICES,
        help_text="¿Las instalaciones, equipo o tubería están libres de sustancias químicas, inflamables, combustibles u oxidantes o están aisladas completamente? (Distancia seguridad 11 metros)"
    )

    riesgos_laborales_vigentes = models.CharField(
        max_length=2,
        choices=ANSWERS_CHOICES,
        help_text="¿El personal está afiliado al sistema general de riesgos laborales y la seguridad social se encuentra al día?"
    )

    aptitud_medica_vigente = models.CharField(
        max_length=2,
        choices=ANSWERS_CHOICES,
        help_text="¿El personal cuenta con certificado de aptitud médica vigente para la labor específica que realizará?"
    )

    observaciones = models.TextField(blank=True, null=True, help_text="Observaciones adicionales (opcional).")

    class Meta:
        verbose_name = "Permiso de Trabajo General"
        verbose_name_plural = "Permisos de Trabajo General"
        ordering = ['-issue_date']



class AuthorizedWorkers(models.Model):
    employee_id = models.ForeignKey('dth.Nomina', on_delete=models.CASCADE)
    sign = models.ImageField(upload_to=get_upload_path, null=True, blank=True)