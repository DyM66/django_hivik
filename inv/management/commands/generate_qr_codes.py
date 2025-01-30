# inv/management/commands/generate_qr_codes.py

from django.core.management.base import BaseCommand
from got.models import Equipo
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Genera y guarda los códigos QR para todos los equipos que aún no los tienen.'

    def handle(self, *args, **options):
        equipos_sin_qr = Equipo.objects.filter(qr_code_url__isnull=True)
        total = equipos_sin_qr.count()
        self.stdout.write(f"Encontrados {total} equipos sin código QR.")

        for idx, equipo in enumerate(equipos_sin_qr, start=1):
            try:
                with transaction.atomic():
                    equipo.generate_qr_code()
                    equipo.save()
                self.stdout.write(f"{idx}/{total}: Código QR generado para el equipo '{equipo.code}'.")
                logger.info(f"Código QR generado para el equipo '{equipo.code}'.")
            except Exception as e:
                self.stderr.write(f"Error al generar QR para el equipo '{equipo.code}': {str(e)}")
                logger.error(f"Error al generar QR para el equipo '{equipo.code}': {str(e)}")

        self.stdout.write(self.style.SUCCESS('Generación de códigos QR completada.'))
