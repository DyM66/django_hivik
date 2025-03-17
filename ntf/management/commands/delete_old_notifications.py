from django.core.management.base import BaseCommand
from ntf.models import Notification
from datetime import timedelta
from django.utils import timezone

class Command(BaseCommand):
    help = "Elimina notificaciones con más de 2 semanas de antigüedad."

    def handle(self, *args, **options):
        fecha_limite = timezone.now() - timedelta(weeks=2)
        
        notificaciones_antiguas = Notification.objects.filter(created_at__lt=fecha_limite)
        total_eliminadas, _ = notificaciones_antiguas.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Se eliminaron correctamente {total_eliminadas} notificaciones con más de 2 semanas de antigüedad."
            )
        )
