from django.db import models
from django.contrib.auth.models import User


class Autorizado(models.Model):
    nombre = models.CharField(max_length=100)
    cargo = models.CharField(max_length=100)
    departamento = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} - {self.cargo}"
    

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
    authorized = models.ForeignKey(Autorizado, on_delete=models.SET_NULL, null=True)

    vehiculo = models.ForeignKey('got.Equipo', on_delete=models.CASCADE)
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
        db_table = 'got_preoperacional'
        ordering = ['-fecha']


# Model 21.2: Preoperacional para estado de vehiculos
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

    vehiculo = models.ForeignKey('got.Equipo', on_delete=models.CASCADE)
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
        db_table = 'got_preoperacionaldiario'
        ordering = ['-fecha']

