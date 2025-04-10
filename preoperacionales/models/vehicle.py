from django.db import models
from got.models import System
from dirtyfields import DirtyFieldsMixin


class Vehicle(DirtyFieldsMixin, models.Model):
    # Relationship with Asset
    system = models.OneToOneField(
        System, on_delete=models.CASCADE, related_name="vehicle"
    )

    # Vehicle fields
    code = models.CharField(primary_key=True, max_length=50)
    type = models.CharField(max_length=20)
    serial = models.CharField(max_length=50)
    brand = models.CharField(max_length=20)
    model = models.CharField(max_length=20)
    plate_number = models.CharField(max_length=6, unique=True)
    color = models.CharField(max_length=20, blank=True, null=True)
    year = models.IntegerField()
    requested_by = models.CharField(max_length=50, blank=True, null=True)
    last_comment = models.TextField(null=True, blank=True)

    # Additional fields
    STATUS_CHOICES = [
        ("AVAILABLE", "Disponible"),
        ("REQUESTED", "Solicitado"),
        ("OCCUPIED", "Ocupado"),
        ("UNDER_MAINTENANCE", "En Mantenimiento"),
        ("OUT_OF_SERVICE", "Fuera de Servicio"),
        ("NOT_AVAILABLE", "No disponible"),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="AVAILABLE",
    )

    def __str__(self):
        return f"{self.brand} {self.model} ({self.plate_number}) - {self.status}"

    class Meta:
        db_table = "vehicle"
        ordering = ["-brand"]
