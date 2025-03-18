# inv/signals.py
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from got.models import ActivityLog, Equipo
from ntf.models import Notification
from django.utils.text import Truncator

@receiver(post_save, sender=Equipo)
def notify_equipo_changes(sender, instance, created, **kwargs):
    """
    Al crearse o actualizarse un Equipo, se aprovecha la lógica del ActivityLog
    para construir un mensaje y notificar al grupo 'inv_members'.
    """
    # 1) Obtenemos el grupo 'inv_members'
    try:
        group = Group.objects.get(name='inv_members')
        users = group.user_set.all()
    except Group.DoesNotExist:
        users = []

    # 2) Determinar acción (creado o modificado)
    if created:
        # Caso: creación
        title = "Equipo creado"
        message = f"El usuario {instance.modified_by.get_full_name() or instance.modified_by.username} ha creado el equipo '{instance.name}'."
    else:
        title = "Equipo modificado"
        now = timezone.now()
        a_minute_ago = now - timezone.timedelta(seconds=60)
        
        logs = ActivityLog.objects.filter(
            model_name='Equipo',
            object_id=instance.pk,
            action='updated',
            timestamp__gte=a_minute_ago
        ).order_by('timestamp')
        
        if logs.exists():
            filtered_logs = [log for log in logs if log.field_name != "horometro"]

            # Si después de excluir 'horometro' ya no quedan cambios => no notificamos
            if not filtered_logs:
                return
            changes = []
            for log in filtered_logs:
                # Muestra "field_name: old_value => new_value"
                changes.append(f"{log.field_name}: {log.old_value} \u2192 {log.new_value}")
            changes_str = "; ".join(changes)
            
            message = (f"El usuario {instance.modified_by.get_full_name() or instance.modified_by.username} "
                       f"ha modificado el equipo '{instance.name}' => {changes_str}")
        else:
            # Si no encontramos logs recientes, hacemos un mensaje genérico
            message = (f"El usuario {instance.modified_by.get_full_name() or instance.modified_by.username} "
                       f"ha modificado el equipo '{instance.name}'. (No hay detalles)")

    # 3) Construir la URL de detalle del equipo
    redirect_url = reverse('got:equipo-detail', kwargs={'pk': instance.pk})

    # 4) Crear la notificación para cada usuario del grupo
    for user in users:
        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            redirect_url=redirect_url
        )


@receiver(pre_delete, sender=Equipo)
def notify_equipo_deleted(sender, instance, **kwargs):
    try:
        group = Group.objects.get(name='inv_members')
        users = group.user_set.all()
    except Group.DoesNotExist:
        users = []

    title = "Equipo eliminado"
    user_display = instance.modified_by.get_full_name() if instance.modified_by else "Desconocido"
    message = f"El usuario {user_display} ha eliminado el equipo '{instance.name}'."

    # Al estar eliminado, no hay redirect_url (ya no existe)
    redirect_url = ""

    for user in users:
        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            redirect_url=redirect_url
        )
