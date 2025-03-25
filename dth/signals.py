# dth/signals.py
from django.db.models.signals import post_delete
from django.dispatch import receiver
from dth.models import Overtime, OvertimeProject

@receiver(post_delete, sender=Overtime)
def auto_delete_project_if_empty(sender, instance, **kwargs):
    """
    Si, tras borrar un registro de Overtime, su proyecto se queda sin más OverTimes,
    eliminar automáticamente el OvertimeProject.
    """
    project = instance.project
    if project:
        # Verificar si el project aún tiene Overtimes asociados
        remaining = project.overtime_set.count()
        if remaining == 0:
            project.delete()
