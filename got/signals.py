from django.db.models.signals import post_save, post_delete, pre_delete, pre_save
from django.dispatch import receiver
from django.db.models import Avg, Sum, Min
from decimal import Decimal
from datetime import datetime
from dth.models import UserProfile
from inv.models import Transaction, Solicitud
from .models import *
from ntf.models import Notification

from got.models.asset import Vessel

@receiver(post_save, sender=Asset)
def create_or_update_vessel_details(sender, instance, created, **kwargs):
    if instance.area == 'a':
        Vessel.objects.get_or_create(asset=instance)


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    instance.profile.save()

@receiver(pre_save, sender=Solicitud)
def update_solicitud_dates(sender, instance, **kwargs):
    if instance.id is not None:
        old_instance = Solicitud.objects.get(id=instance.id)
        
        if not old_instance.approved and instance.approved:
            instance.approval_date = timezone.now()

        if not old_instance.num_sc and instance.num_sc:
            instance.sc_change_date = timezone.now()

        if not old_instance.num_sc and instance.cancel:
            instance.cancel_date = timezone.now()

@receiver(post_save, sender=HistoryHour)
@receiver(post_delete, sender=HistoryHour)
def update_equipo_horometro(sender, instance, **kwargs):
    equipo = instance.component
    ultimos_10_registros = HistoryHour.objects.filter(component=equipo).order_by('-report_date')[:15]
    promedio_horas = ultimos_10_registros.aggregate(promedio_horas=Avg('hour'))['promedio_horas']
    equipo.prom_hours = promedio_horas or 0
    equipo.horometro = equipo.calculate_horometro()
    equipo.save()
    # update_fuel_consumption_for_asset(equipo, instance.report_date)


@receiver(pre_save)
def track_model_changes_pre_save(sender, instance, **kwargs):
    # Solo rastrear los modelos que tienen el campo modified_by
    if hasattr(instance, 'modified_by'):
        # Almacenar los valores anteriores
        if instance.pk:  # Solo si el objeto ya existe
            try:
                instance._original_state = sender.objects.get(pk=instance.pk)
            except sender.DoesNotExist:
                instance._original_state = None

@receiver(post_save)
def track_model_changes_post_save(sender, instance, **kwargs):
    try:
        if hasattr(instance, 'modified_by'):
            if hasattr(instance, '_original_state') and instance._original_state:
                original_instance = instance._original_state
                # Comparar los campos modificados
                for field in instance._meta.fields:
                    field_name = field.name
                    old_value = getattr(original_instance, field_name)
                    new_value = getattr(instance, field_name)

                    if old_value != new_value:  # Si el valor cambió
                        # Guardar en el registro de actividad
                        ActivityLog.objects.create(
                            user_name=instance.modified_by.username,
                            action='updated',
                            model_name=sender.__name__,
                            object_id=instance.pk,
                            # field_name=field_name,
                            field_name=get_verbose_name_or_fallback(sender, field_name),
                            old_value=str(old_value),
                            new_value=str(new_value),
                            timestamp=timezone.now()
                        )
            else:
                # Si es una creación
                ActivityLog.objects.create(
                    user_name=instance.modified_by.username,
                    action='created',
                    model_name=sender.__name__,
                    object_id=instance.pk,
                    timestamp=timezone.now()
                )
    except AttributeError:
        # Si falta algún atributo (por ejemplo, 'modified_by'), no se hace nada
        pass
    except Exception as e:
        # Manejar otros errores si es necesario (registro en logs, etc.)
        pass

@receiver(pre_delete)
def track_model_deletion(sender, instance, **kwargs):
    # Solo rastrear los modelos que tienen el campo modified_by
    if hasattr(instance, 'modified_by'):
        # Guardar el registro de eliminación
        ActivityLog.objects.create(
            user_name=instance.modified_by.username if instance.modified_by else "Unknown",
            action='deleted',
            model_name=sender.__name__,
            object_id=instance.pk,
            timestamp=timezone.now()
        )

def get_verbose_name_or_fallback(sender, field_name):
    """
    Retorna el verbose_name del campo si existe, 
    en caso contrario retorna field_name tal cual.
    """
    try:
        field = sender._meta.get_field(field_name)
        return str(field.verbose_name).capitalize()  # O retórnalo tal cual, si no deseas capitalizar
    except:
        return field_name  # fallback en caso de error


@receiver(post_save, sender=Ruta)
def update_asset_compliance_after_ruta_save(sender, instance, **kwargs):
    """
    Cada vez que se guarde un Ruta, actualizamos el compliance del Asset
    relacionado con su 'system'.
    """
    system = instance.system
    if system and system.asset:
        system.asset.update_maintenance_compliance_cache()

@receiver(post_save, sender=HistoryHour)
def update_asset_compliance_after_hours_save(sender, instance, **kwargs):
    """
    Cada vez que se guarde un HistoryHour, recalculamos el compliance 
    del Asset relacionado con equipo->system->asset.
    """
    equipo = instance.component
    if equipo and equipo.system and equipo.system.asset:
        equipo.system.asset.update_maintenance_compliance_cache()


@receiver(post_save, sender=Ot)
def update_asset_compliance_after_ot_save(sender, instance, **kwargs):
    """
    Cada vez que se guarde una OT, recalculamos el compliance 
    del Asset relacionado con su 'system'.
    Opcional: filtrar si solo quieres recalcular cuando la OT esté finalizada, etc.
    """
    system = instance.system
    if system and system.asset:
        # Ejemplo: recalcular solo si la OT está finalizada
        # if instance.state == 'f':
        #     system.asset.update_maintenance_compliance_cache()

        # O recalcular siempre que se guarde
        if instance.state == 'f':
            system.asset.update_maintenance_compliance_cache()


from django.utils.text import Truncator
from django.contrib.auth.models import Group
@receiver(post_save, sender=Solicitud)
def create_solicitud_notification(sender, instance, created, **kwargs):
    if created:
        group_name = 'mto_members' if instance.dpto == 'm' else 'operaciones' # Determinar el grupo de destino según el departamento:
        full_name = instance.solicitante.get_full_name() or instance.solicitante.username
        
        # Determinar el asset asociado
        if instance.ot:
            asset_name = instance.ot.system.asset.name
            ot_name = Truncator(instance.ot.description).chars(50)
            title = f"Nueva RQ para {asset_name} OT{instance.ot.num_ot}: {ot_name}"
        elif instance.asset:
            asset_name = instance.asset.name
            title = f"Nueva RQ para {asset_name}"
        else:
            asset_name = "N/D"  # No disponible
        
        # Truncar el texto de suministros a 100 caracteres (puedes ajustar el límite)
        suministros_desc = instance.suministros or ""
        suministros_truncated = Truncator(suministros_desc).chars(150)
        
        # Construir el mensaje de notificación
        message = f"{full_name}/ {suministros_truncated}"

        # Calcular el número de página en la vista de Solicitudes
        page_size = 20  # Según paginate_by en SolicitudesListView
        # Como el listado se ordena descendientemente por creation_date, contamos las solicitudes más nuevas
        newer_count = Solicitud.objects.filter(creation_date__gt=instance.creation_date).count()
        page_number = (newer_count // page_size) + 1

        # Construir la URL de redirección; se añade un ancla para identificar la solicitud
        redirect_url = reverse('got:rq-list') + f"?page={page_number}#solicitud-{instance.id}"

        
        # Obtener el grupo y los usuarios destinatarios
        try:
            group = Group.objects.get(name=group_name)
            users = group.user_set.all()
        except Group.DoesNotExist:
            users = []
        
         # Crear la notificación para cada usuario del grupo
        for user in users:
            Notification.objects.create(
                user=user,
                title=title,
                message=message,
                redirect_url=redirect_url
            )


@receiver(post_save, sender=FailureReport)
def create_failure_report_notification(sender, instance, created, **kwargs):
    if created:
        # Determinar asset a partir del equipo
        if instance.equipo and instance.equipo.system and instance.equipo.system.asset:
            asset_name = instance.equipo.system.asset.name
        else:
            asset_name = "N/D"
        
        reporter = instance.modified_by.get_full_name() if instance.modified_by else "Sistema"
        title = f"Nuevo reporte de falla para {asset_name}"
        
        description_truncated = Truncator(instance.description).chars(150)
        # Incluir enlace al detalle del reporte de falla
        message = f"{reporter}/ {instance.equipo.name}: {description_truncated}"
        redirect_url = instance.get_absolute_url()
        
        # Notificar a usuarios del grupo 'mto_members'
        try:
            group_super = Group.objects.get(name="mto_members")
            users_super = group_super.user_set.all()
        except Group.DoesNotExist:
            users_super = []
        for user in users_super:
            Notification.objects.create(
                user=user,
                title=title,
                message=message,
                redirect_url=redirect_url
            )
        
        # Si el campo impact incluye 'o', notificar también al grupo 'operaciones'
        if 'o' in instance.impact:
            try:
                group_operaciones = Group.objects.get(name="operaciones")
                users_operaciones = group_operaciones.user_set.all()
            except Group.DoesNotExist:
                users_operaciones = []
            for user in users_operaciones:
                Notification.objects.create(
                    user=user,
                    title=title,
                    message=message,
                    redirect_url=redirect_url
                )



@receiver(post_save, sender=Solicitud)
def notify_tramitado_solicitud(sender, instance, created, **kwargs):
    # Solo se dispara al actualizar (no en la creación)
    if created:
        return

    # Verificamos si la solicitud está en estado "Tramitado"
    # (según tu lógica: aprobada y con sc_change_date asignado)
    if instance.approved and instance.sc_change_date:
        # Obtenemos el asset asociado; si la solicitud tiene OT, se obtiene a través de ésta, si no, se usa el asset directamente
        asset = instance.ot.system.asset if instance.ot else instance.asset
        if not asset:
            return

        asset_name = asset.name
        title = f"Solicitud Tramitada para {asset_name}"
        # Truncamos la descripción de suministros para incluirla en el mensaje
        supplies_truncated = Truncator(instance.suministros).chars(100)
        # Preparamos el mensaje, incluyendo el valor de num_sc y el usuario que tramitó (suponiendo que se registra en approved_by)
        message = f"Se ha aprobado y tramitado la solicitud de compra: {supplies_truncated} - SC: {instance.num_sc}. Tramita: {instance.approved_by}."

        # Opcional: podemos construir una URL de redirección similar a la de las notificaciones de creación
        page_size = 20  # Debe coincidir con paginate_by en tu vista de solicitudes
        newer_count = Solicitud.objects.filter(creation_date__gt=instance.creation_date).count()
        page_number = (newer_count // page_size) + 1
        redirect_url = reverse('got:rq-list') + f"?page={page_number}#solicitud-{instance.id}"

        # Notificar al supervisor y al capitán del asset (si existen)
        for role in ['supervisor', 'capitan']:
            user = getattr(asset, role, None)
            if user:
                Notification.objects.create(
                    user=user,
                    title=title,
                    message=message,
                    redirect_url=redirect_url
                )
