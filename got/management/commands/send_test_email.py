from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail
from django.conf import settings

class Command(BaseCommand):
    """
    A management command to send a test email to the default email address
    specified in the settings.
    """
    help = 'Sends a test email to the email address set in settings.EMAIL_HOST_USER'

    def handle(self, *args, **options):
        subject = "Test Email from Django"
        message = "¡Hola! Este es un correo de prueba para verificar la configuración de envío de correos."
        from_email = settings.EMAIL_HOST_USER
        recipient_list = [settings.EMAIL_HOST_USER]

        if not from_email:
            raise CommandError(
                "No se encontró el EMAIL_HOST_USER en las variables de entorno "
                "o en la configuración de Django."
            )

        try:
            send_mail(subject, message, from_email, recipient_list)
            self.stdout.write(self.style.SUCCESS(
                f'Se ha enviado un correo de prueba a: {recipient_list}.'
            ))
        except Exception as e:
            raise CommandError(
                f'Error al enviar el correo: {e}'
            )
