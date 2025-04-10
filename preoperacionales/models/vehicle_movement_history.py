from django.db import models
from .vehicle import Vehicle


class VehicleMovementHistory(models.Model):
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.CASCADE, related_name="movement_history"
    )
    movement_time = models.DateTimeField(auto_now_add=True)
    action = models.CharField(
        max_length=20,
        choices=[
            ("ENTRY", "Entrada"),
            ("EXIT", "Salida"),
            ("MAINTENANCE_IN", "Entrada a Mantenimiento"),
            ("MAINTENANCE_OUT", "Salida de Mantenimiento"),
            ("SERVICE_IN", "Habilitado"),
            ("SERVICE_OUT", "Fuera de Servicio"),
        ],
    )
    requested_by = models.CharField(max_length=50, null=True, blank=True)
    comment = models.CharField(max_length=250, blank=True, null=True)

    class Meta:
        db_table = "vehicle_movement_history"
        ordering = ["-movement_time"]

    def __str__(self):
        return f"{self.action.title()} de {self.vehicle} - {self.movement_time}"
