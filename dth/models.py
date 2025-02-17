from django.db import models
from django.contrib.auth.models import User
from got.paths import get_upload_path  # Puedes copiar o reutilizar la función get_upload_path

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    cargo = models.CharField(max_length=100, null=True, blank=True)
    firma = models.ImageField(upload_to=get_upload_path, null=True, blank=True)
    dpto = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        # Es muy importante conservar el mismo nombre de tabla para que Django no intente crear una nueva.
        db_table = 'got_userprofile'
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"

    def __str__(self):
        return f"{self.user.username}'s profile"
    

class Overtime(models.Model):
    CARGO = (
        ('a', 'Capitán'),
        ('b', 'Primer Oficial de Puente'),
        ('c', 'Marino'),
        ('d', 'Jefe de Máquinas'),
        ('e', 'Primer Oficial de Máquinas'),
        ('f', 'Maquinista'),
        ('g', 'Otro'),
    )

    # Información común
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    justificacion = models.TextField()

    # Información específica por persona
    nombre_completo = models.CharField(max_length=200, default='')
    cedula = models.CharField(max_length=20, default='')
    cargo = models.CharField(max_length=1, choices=CARGO)

    # Información adicional
    reportado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    approved = models.BooleanField(default=False)
    asset = models.ForeignKey('got.Asset', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.nombre_completo} - {self.get_cargo_display()} ({self.fecha})"

    class Meta:
        db_table = 'got_overtime'
        permissions = [
            ('can_approve_overtime', 'Puede aprobar horas extras'),
        ]
