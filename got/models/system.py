from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse

from got.models.asset import Asset


class System(models.Model):
    STATUS = (('m', 'Mantenimiento'), ('o', 'Operativo'), ('x', 'Fuera de servicio'), ('s', 'Stand by'))
    name = models.CharField(max_length=50)
    location = models.CharField(max_length=50, default="Cartagena", null=True, blank=True)
    state = models.CharField(choices=STATUS, default='o', max_length=1)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, to_field='abbreviation')
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    
    def __str__(self):
        return '%s/ %s' % (self.asset, self.name)

    def get_absolute_url(self):
        return reverse('got:sys-detail', args=[self.id])

    class Meta:
        ordering = ['asset__name', 'name']