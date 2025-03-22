# inv/signals.py
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from got.models import ActivityLog, Equipo
from ntf.models import Notification
from django.utils.text import Truncator

# @receiver(post_save, sender=Equipo)
# def notify_equipo_changes(sender, instance, created, **kwargs):
#     EXCLUDED_FIELDS = {"horometro", "prom_hours"}

#     # Revisar los campos modificados usando DirtyFieldsMixin
#     dirty_fields = instance.get_dirty_fields().keys()

#     # Si no se creó, sino que se modificó, verificamos campos modificados
#     if not created:
#         modified_fields_set = set(dirty_fields)

#         # Si todos los campos modificados están en los excluidos, no notificamos
#         if modified_fields_set.issubset(EXCLUDED_FIELDS):
#             return  # No enviar notificación, sólo se modificaron campos excluidos

#     # Procede normalmente si se creó el objeto o se modificaron otros campos
#     try:
#         group = Group.objects.get(name='inv_members')
#         users = group.user_set.all()
#     except Group.DoesNotExist:
#         users = []

#     asset_name = instance.system.asset.name if (instance.system and instance.system.asset) else "Desconocido"

#     if created:
#         title = f"Equipo creado en {asset_name}"    
#         message = f"El usuario {instance.modified_by.get_full_name() or instance.modified_by.username} ha creado el equipo '{instance.name}'."
#     else:
#         title = f"Equipo modificado en {asset_name}"
#         now = timezone.now()
#         a_minute_ago = now - timezone.timedelta(seconds=60)
        
#         logs = ActivityLog.objects.filter(
#             model_name='Equipo',
#             object_id=instance.pk,
#             action='updated',
#             timestamp__gte=a_minute_ago
#         ).order_by('timestamp')

#         filtered_logs = [log for log in logs if log.field_name not in EXCLUDED_FIELDS]

#         if filtered_logs:
#             changes = [
#                 f"{log.field_name}: {log.old_value} \u2192 {log.new_value}"
#                 for log in filtered_logs
#             ]
#             changes_str = "; ".join(changes)
            
#             message = (f"El usuario {instance.modified_by.get_full_name() or instance.modified_by.username} "
#                        f"ha modificado el equipo '{instance.name}' => {changes_str}")
#         else:
#             # Si solo había cambios en campos excluidos, pero ya filtramos antes,
#             # Este bloque sólo ocurre si no hay registros recientes (raro).
#             message = (f"El usuario {instance.modified_by.get_full_name() or instance.modified_by.username} "
#                        f"ha modificado el equipo '{instance.name}'. (Sin detalles recientes)")

#     redirect_url = reverse('got:equipo-detail', kwargs={'pk': instance.pk})

#     for user in users:
#         Notification.objects.create(
#             user=user,
#             title=title,
#             message=message,
#             redirect_url=redirect_url
#         )


@receiver(pre_delete, sender=Equipo)
def notify_equipo_deleted(sender, instance, **kwargs):
    try:
        group = Group.objects.get(name='inv_members')
        users = group.user_set.all()
    except Group.DoesNotExist:
        users = []

    asset_name = instance.system.asset.name if (instance.system and instance.system.asset) else "Desconocido"
    title = f"Equipo eliminado en {asset_name}"
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
