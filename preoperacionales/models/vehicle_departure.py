from django.db import models
from django.contrib.auth.models import User
from .authorizer import Authorizer


class Preoperacional(models.Model):

    RUTA = (("u", "Urbana"), ("r", "Rural"), ("m", "Mixta (Urbana y Rural)"))

    fecha = models.DateTimeField(auto_now_add=True)
    reporter = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    nombre_no_registrado = models.CharField(max_length=100, null=True, blank=True)
    cedula = models.CharField(max_length=20)
    kilometraje = models.IntegerField()
    motivo = models.TextField()
    salida = models.CharField(max_length=150)
    destino = models.CharField(max_length=150)
    tipo_ruta = models.CharField(max_length=1, choices=RUTA)

    authorizer = models.ForeignKey(Authorizer, on_delete=models.SET_NULL, null=True)

    vehiculo = models.ForeignKey("got.Equipo", on_delete=models.CASCADE)
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
        db_table = "got_preoperacional"
        ordering = ["-fecha"]
