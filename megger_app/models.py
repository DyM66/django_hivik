from django.db import models
from got.models import Ot, Equipo


# Model 21: Registros de pruebas megger (Pruebas de aislamiento)
class Megger(models.Model):
    ot = models.ForeignKey(Ot, on_delete=models.CASCADE)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE)
    date_report = models.DateField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"Prueba #{self.id}/{self.equipo}"

    class Meta:
        db_table = 'got_megger'


# Model 21.1: 
class Estator(models.Model):

    TEST_TYPE_CHOICES = (
        ('i', 'Prueba Inicial'),
        ('f', 'Prueba Final'),
    )

    TIME_TYPE_CHOICES = (
        ('1', '1 min'),
        ('2', '10 min'),
    )

    megger = models.ForeignKey(Megger, on_delete=models.CASCADE)
    test_type = models.CharField(max_length=1, choices=TEST_TYPE_CHOICES, default='i')
    time_type = models.CharField(max_length=1, choices=TIME_TYPE_CHOICES, default='1')
    pi_1min_l1_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_1min_l2_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_1min_l3_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_1min_l1_l2 = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_1min_l2_l3 = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_1min_l3_l1 = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_obs_l1_tierra = models.TextField(null=True, blank=True)
    pi_obs_l2_tierra = models.TextField(null=True, blank=True)
    pi_obs_l3_tierra = models.TextField(null=True, blank=True)
    pi_obs_l1_l2 = models.TextField(null=True, blank=True)
    pi_obs_l2_l3 = models.TextField(null=True, blank=True)
    pi_obs_l3_l1 = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'got_estator'


# Model 21.2
class Excitatriz(models.Model):

    TEST_TYPE_CHOICES = (
        ('i', 'Prueba Inicial'),
        ('f', 'Prueba Final'),
    )

    megger = models.ForeignKey(Megger, on_delete=models.CASCADE)
    test_type = models.CharField(max_length=1, choices=TEST_TYPE_CHOICES, default='i')
    pi_1min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_10min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_obs_l_tierra = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'got_excitatriz'


# Model 21.3
class RotorMain(models.Model):

    TEST_TYPE_CHOICES = (
        ('i', 'Prueba Inicial'),
        ('f', 'Prueba Final'),
    )

    megger = models.ForeignKey(Megger, on_delete=models.CASCADE)
    test_type = models.CharField(max_length=1, choices=TEST_TYPE_CHOICES, default='i')

    pi_1min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_10min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_obs_l_tierra = models.TextField(null=True, blank=True)

    pf_1min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_10min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_obs_l_tierra = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'got_rotormain'


# Model 21.4
class RotorAux(models.Model):

    TEST_TYPE_CHOICES = (
        ('i', 'Prueba Inicial'),
        ('f', 'Prueba Final'),
    )

    megger = models.ForeignKey(Megger, on_delete=models.CASCADE)
    test_type = models.CharField(max_length=1, choices=TEST_TYPE_CHOICES, default='i')

    pi_1min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_10min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pi_obs_l_tierra = models.TextField(null=True, blank=True)

    pf_1min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_10min_l_tierra = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    pf_obs_l_tierra = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'got_rotoraux'


# Model 21.5
class RodamientosEscudos(models.Model):

    TEST_TYPE_CHOICES = (
        ('i', 'Prueba Inicial'),
        ('f', 'Prueba Final'),
    )

    megger = models.ForeignKey(Megger, on_delete=models.CASCADE)
    test_type = models.CharField(max_length=1, choices=TEST_TYPE_CHOICES, default='i')

    rodamientoas = models.TextField(null=True, blank=True)
    rodamientobs = models.TextField(null=True, blank=True)
    escudoas = models.TextField(null=True, blank=True)
    escudobs = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'got_rodamientosescudos'