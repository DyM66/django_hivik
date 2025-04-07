from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from got.models.equipment import Equipo
from got.models.routine import Ruta
from got.paths import get_upload_path
from outbound.models import Place

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

    def calculate_maintenance_compliance(self):
        systems = self.system_set.all()
        all_rutas = Ruta.objects.filter(system__in=systems)
        total_niveles = sum(ruta.nivel for ruta in all_rutas)

        if total_niveles == 0:
            return None

        compliant_weight = 0
        for ruta in all_rutas:
            if ruta.next_date >= timezone.now().date():
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
        ordering = ['area', 'name']


class Vessel(models.Model):
    asset = models.OneToOneField(Asset, on_delete=models.CASCADE, related_name='vessel_details')

    vessel_type = models.CharField(max_length=100, null=True, blank=True)
    navigation_type = models.CharField(max_length=100, null=True, blank=True)
    trade_type = models.CharField(max_length=100, null=True, blank=True)

    flag = models.CharField(default='Colombia', max_length=50, null=True, blank=True)
    length = models.DecimalField(default=0, max_digits=8, decimal_places=2, null=True, blank=True)  # eslora
    beam = models.DecimalField(default=0, max_digits=8, decimal_places=2, null=True, blank=True)    # manga
    depth = models.DecimalField(default=0, max_digits=8, decimal_places=2, null=True, blank=True)   # puntal
    draft = models.DecimalField(default=0, max_digits=8, decimal_places=2, null=True, blank=True)   # calado
    material = models.CharField(max_length=100, null=True, blank=True)
    deadweight = models.IntegerField(default=0, null=True, blank=True)
    gross_tonnage = models.IntegerField(default=0, null=True, blank=True)  # arqueo_bruto
    net_tonnage = models.IntegerField(default=0, null=True, blank=True)    # arqueo_neto
    power_kw = models.DecimalField(default=0, max_digits=8, decimal_places=2, null=True, blank=True)
    year_built = models.PositiveIntegerField(null=True, blank=True)
    bollard_pull = models.DecimalField(default=0, max_digits=8, decimal_places=2, null=True, blank=True)

    @property
    def capacidad_fo(self):
        total = Equipo.objects.filter(system__asset=self, type__code='k', tipo_almacenamiento='Combustible').aggregate(total_volumen=models.Sum('volumen'))['total_volumen'] or 0
        return total 

    def __str__(self):
        return f"Vessel Details - {self.asset.name}"

