from django.db import models
from django.contrib.auth.models import User
from got.paths import *

# Model 4: Servicios
class Service(models.Model):
    description = models.CharField(max_length=200, unique=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.description

    class Meta:
        ordering = ['description']