# dth/models/lookups.py
from django.db import models

class EPS(models.Model):
    """
    Catálogo de EPS disponible, 
    con la lista larga que proporcionaste (Coosalud, Nueva EPS, etc.).
    """
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name