# mto/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from got.models import Ruta
from mto.utils import create_maintenance_plan_for_ruta
from datetime import date

@receiver(post_save, sender=Ruta)
def create_plan_on_ruta_creation(sender, instance, created, **kwargs):
    if created:
        # Definir el período para el plan (por ejemplo, de febrero 2025 a diciembre 2025)
        period_start = date(2025, 2, 1)
        period_end = date(2025, 12, 31)
        # Crear el plan si no existe ya para este período
        plan = create_maintenance_plan_for_ruta(instance, period_start, period_end)
        if plan:
            print(f"Se creó automáticamente un plan (ID: {plan.id}) para la ruta '{instance.name}'")
