# tic/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Ticket
from django.contrib.auth.models import User
from got.models import Notification
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

@receiver(post_save, sender=Ticket)
def notify_admins_on_ticket_creation(sender, instance, created, **kwargs):
    if created:
        subject = f"Nuevo Ticket de Soporte Técnico - Reporte #{instance.id}"

        context = {
            'ticket': instance,
            'reporter': instance.reporter,
            # Asumimos que tienes definida la URL base en settings o puedes construirla dinámicamente
            'ticket_detail_url': f"https://got.serport.co/tic/tickets/{instance.id}/",
        }
        # Renderizar el contenido HTML del correo usando un template
        message_html = render_to_string("emails/ticket_notification.html", context)
        
        # También construimos un mensaje de texto plano por si el cliente no soporta HTML
        message_text = (
            f"Nuevo Ticket de Soporte Técnico\n\n"
            f"Ticket #{instance.id} - {instance.title}\n"
            f"Reportado por: {instance.reporter.get_full_name()} ({instance.reporter.email})\n"
            f"Tipo: {instance.get_ticket_type_display()}\n"
            f"Categoría: {instance.get_category_display()}\n\n"
            f"Mensaje:\n{instance.message}\n\n"
            f"Ver detalle: https://got.serport.co/tickets/{instance.id}/"
        )

        message = (
            f"Ticket #{instance.id} creado por {instance.reporter.get_full_name()}.\n"
            f"Fecha y hora: {instance.created_at}\n"
            f"Tipo: {instance.ticket_type}\n"
            f"Categoría: {instance.category}\n"
            f"Mensaje:\n{instance.message}"
        )
        admin_users = User.objects.filter(groups__name="tic_members")
        recipient_list = [admin.email for admin in admin_users if admin.email]
        if recipient_list:
            email = EmailMultiAlternatives(subject, message_text, settings.EMAIL_HOST_USER, recipient_list)
            email.attach_alternative(message_html, "text/html")
            email.send(fail_silently=True)

        for admin in admin_users:
            Notification.objects.create(user=admin, title=subject, message=message, redirect_url=f"/tic/tickets/{instance.id}/")
