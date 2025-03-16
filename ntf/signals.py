# ntf/signals.py
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils.text import Truncator
from django.utils import timezone
from inv.models import Solicitud
from .models import Notification, WebPushSubscription
from .utils import send_push_notification

@receiver(post_save, sender=Solicitud)
def create_solicitud_notification(sender, instance, created, **kwargs):
    if created:
        group_name = 'super_members' if instance.dpto == 'm' else 'operaciones'
        full_name = instance.solicitante.get_full_name() or instance.solicitante.username

        if instance.ot:
            asset_name = instance.ot.system.asset.name
            ot_name = Truncator(instance.ot.description).chars(50)
            title = f"Nueva RQ para {asset_name} OT{instance.ot.num_ot}: {ot_name}"
        elif instance.asset:
            asset_name = instance.asset.name
            title = f"Nueva RQ para {asset_name}"
        else:
            asset_name = "N/D"
        
        suministros_truncated = Truncator(instance.suministros or "").chars(150)
        page_size = 20
        newer_count = Solicitud.objects.filter(creation_date__gt=instance.creation_date).count()
        page_number = (newer_count // page_size) + 1
        redirect_url = reverse('got:rq-list') + f"?page={page_number}#solicitud-{instance.id}"
        try:
            group = Group.objects.get(name=group_name)
            users = group.user_set.all()
        except Group.DoesNotExist:
            users = []
        
        # Crear la notificación para cada usuario y enviar push
        for user in users:
            notification = Notification.objects.create(
                user=user,
                title=title,
                message=f"{full_name}/ {suministros_truncated}",
                redirect_url=redirect_url
            )
            # Enviar notificación push a cada suscripción del usuario
            subscriptions = user.push_subscriptions.all()
            payload = {
                "title": notification.title,
                "message": notification.message,
                "redirect_url": notification.redirect_url,
                "created_at": notification.created_at.strftime("%d/%m/%Y %H:%M")
            }
            for sub in subscriptions:
                send_push_notification(sub, payload)
