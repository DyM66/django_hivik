# En got/management/commands/recalc_trans_reports.py

from django.core.management.base import BaseCommand, CommandError
from got.models import Asset, Transaction
from django.db.models import Q
from datetime import datetime, timedelta
from decimal import Decimal

class Command(BaseCommand):
    help = 'Recalcula los valores reportados de las transacciones (cant_report y cant_report_transf) para todos los suministros de un asset dado'

    def add_arguments(self, parser):
        parser.add_argument('asset_abbreviation', type=str, help='Abreviatura del asset para el cual recalcular las transacciones')

    def handle(self, *args, **options):
        asset_abbr = options['asset_abbreviation']
        try:
            asset = Asset.objects.get(abbreviation=asset_abbr)
        except Asset.DoesNotExist:
            raise CommandError(f"Asset con abreviatura '{asset_abbr}' no existe.")
        
        self.stdout.write(f"Recalculando transacciones para el asset: {asset.name} ({asset.abbreviation})")

        # Iteramos por cada suministro asociado al asset
        supplies = asset.suministros.all()
        for supply in supplies:
            self.stdout.write(f"Procesando suministro: {supply}")
            # Tomamos la cantidad actual del suministro como base
            current_qty = supply.cantidad or Decimal('0.00')
            # Obtenemos las transacciones relacionadas con este suministro (tanto en el campo 'suministro' como en 'suministro_transf')
            transactions = Transaction.objects.filter(
                Q(suministro=supply) | Q(suministro_transf=supply)
            ).order_by('-fecha', '-id')
            # Iteramos de la transacción más reciente a la más antigua
            for trans in transactions:
                if trans.tipo == 'i':  # Ingreso: se sumó producto, por lo tanto el reporte anterior es current_qty - cantidad
                    new_report = current_qty - trans.cant
                    trans.cant_report = new_report
                    self.stdout.write(f"Transacción {trans.id} (Ingreso): cantidad={trans.cant} -> nuevo cant_report={new_report}")
                elif trans.tipo == 'c':  # Consumo: se consumió producto, por lo que el reporte anterior es current_qty + cantidad
                    new_report = current_qty + trans.cant
                    trans.cant_report = new_report
                    self.stdout.write(f"Transacción {trans.id} (Consumo): cantidad={trans.cant} -> nuevo cant_report={new_report}")
                elif trans.tipo == 't':  # Transferencia
                    # Si este suministro es el emisor (saliente)
                    if trans.suministro == supply:
                        new_report = current_qty + trans.cant
                        trans.cant_report = new_report
                        self.stdout.write(f"Transacción {trans.id} (Transferencia Saliente): cantidad={trans.cant} -> nuevo cant_report={new_report}")
                    # Si es el receptor (entrante)
                    elif trans.suministro_transf == supply:
                        new_report = current_qty - trans.cant
                        trans.cant_report_transf = new_report
                        self.stdout.write(f"Transacción {trans.id} (Transferencia Entrante): cantidad={trans.cant} -> nuevo cant_report_transf={new_report}")
                    else:
                        self.stdout.write(f"Transacción {trans.id} (Transferencia): suministro no coincide, se omite.")
                        continue
                else:
                    self.stdout.write(f"Transacción {trans.id}: tipo desconocido, se omite.")
                    continue

                # Guardamos la transacción actualizada (solo los campos que cambiamos)
                trans.save(update_fields=['cant_report', 'cant_report_transf'])
                # Actualizamos la cantidad actual para el siguiente registro
                current_qty = new_report
            self.stdout.write(self.style.SUCCESS(f"Finalizado el recálculo para el suministro {supply}"))
        
        self.stdout.write(self.style.SUCCESS("Recalculo completado para todos los suministros del asset."))
