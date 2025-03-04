# con/management/commands/create_assetcosts.py
from decimal import Decimal
from django.core.management.base import BaseCommand
from got.models import Asset
from cont.models import AssetCost

class Command(BaseCommand):
    help = "Crea registros AssetCost para cada Asset en áreas 'a' y 'c' que no tengan registro"

    def handle(self, *args, **options):
        assets = Asset.objects.filter(area__in=['a', 'c'])
        created = 0
        for asset in assets:
            # Si el asset no tiene atributo cost_info (relación OneToOne definida)
            if not hasattr(asset, 'cost_info'):
                AssetCost.objects.create(
                    asset=asset,
                    initial_cost=Decimal('0.00'),
                    costo_adicional=Decimal('0.00')
                )
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Se han creado {created} registros de AssetCost."))
