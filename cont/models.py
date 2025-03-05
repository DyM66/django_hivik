# con/models.py
from decimal import Decimal
from django.db import models, transaction
from got.models import Asset
from django.utils import timezone
from dateutil.relativedelta import relativedelta

class AssetCost(models.Model):
    asset = models.OneToOneField(Asset, on_delete=models.CASCADE, related_name='cost_info', limit_choices_to={'area__in': ['a', 'c']})
    initial_cost = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True, help_text="Valor monetario de adquisición (COP)")
    costo_adicional = models.DecimalField(max_digits=18, decimal_places=2, default=0, help_text="Suma de montos de financiaciones (COP)")
    fp = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True, help_text="Factor de participación (entre 0 y 1)")

    # Campos que antes estaban en Supuesto:
    valor_financiacion = models.DecimalField(max_digits=18, decimal_places=2, default=0, help_text="Valor de la financiación generado por la tasa de interés")


    def save(self, *args, **kwargs):
        with transaction.atomic():
            super().save(*args, **kwargs)
            # Sumar initial_cost y costo_adicional para cada asset
            # assets = AssetCost.objects.filter(asset__area=self.asset.area)
            assets = AssetCost.objects.all()
            total_area = sum(
                (ac.initial_cost or Decimal('0')) + (ac.costo_adicional or Decimal('0'))
                for ac in assets
            )
            if total_area > 0:
                for ac in assets:
                    asset_total = (ac.initial_cost or Decimal('0')) + (ac.costo_adicional or Decimal('0'))
                    ac.fp = asset_total / total_area
                    AssetCost.objects.filter(pk=ac.pk).update(fp=ac.fp)
            else:
                AssetCost.objects.filter(asset__area=self.asset.area).update(fp=None)

    @property
    def cont_a_los_gastos(self):
        """
        Calcula la contribución a los gastos de forma dinámica:
          - Suma el promedio mensual de todos los registros de GastosAdministrativos.
          - Multiplica el resultado por el factor de participación (fp) de este asset.
        """
        # Importar localmente para evitar problemas de importación circular
        from .models import GastosAdministrativos
        gastos = GastosAdministrativos.objects.all()
        total_promedio = sum(g.promedio_mes for g in gastos)
        if self.fp is not None:
            return total_promedio * self.fp
        return None

    @property
    def gastos_calculados(self):
        """
        Suma de todos los promedios mensuales de GastosAdministrativos multiplicado por el fp del AssetCost asociado.
        """
        total = sum(g.promedio_mes for g in GastosAdministrativos.objects.all())
        return total * self.asset_cost.fp if self.asset_cost.fp is not None else None

    def __str__(self):
        return f"Cost info for {self.asset}"


class Financiacion(models.Model):
    asset_cost = models.ForeignKey(AssetCost, on_delete=models.CASCADE, related_name="financiaciones", null=True, blank=True)
    monto = models.DecimalField(max_digits=18, decimal_places=2, help_text="Monto del préstamo (COP)")
    plazo = models.PositiveIntegerField(help_text="Plazo en meses")
    fecha_desembolso = models.DateField()
    fecha_vencimiento = models.DateField()
    tasa_interes = models.DecimalField(max_digits=5, decimal_places=4, help_text="Tasa de interés (ej. 0.05 para 5%)")
    no_deuda = models.CharField(max_length=50, help_text="Número de deuda")
    periodicidad_pago = models.CharField(max_length=20, default="mensual", help_text="Periodicidad del pago de interés")
    valor_financiacion = models.DecimalField(
        max_digits=18, 
        decimal_places=2, 
        blank=True, 
        null=True,
        help_text="Valor generado por la tasa de interés"
    )

    @property
    def fecha_vencimiento(self):
        """Calcula la fecha de vencimiento sumando el plazo en meses a la fecha de desembolso."""
        return self.fecha_desembolso + relativedelta(months=self.plazo)

    def save(self, *args, **kwargs):
        # Calcular valor_financiacion (para periodicidad mensual se asume: monto*tasa/12)
        if self.periodicidad_pago.lower() == "mensual":
            self.valor_financiacion = (self.monto * self.tasa_interes) / Decimal('12')
        else:
            self.valor_financiacion = (self.monto * self.tasa_interes) / Decimal('12')
        super().save(*args, **kwargs)
        # Actualizar costo_adicional del registro unificado
        asset_cost = self.asset_cost
        total_monto = sum(fin.monto for fin in asset_cost.financiaciones.all())
        asset_cost.costo_adicional = total_monto
        asset_cost.save()

    def __str__(self):
        return f"Financiación {self.no_deuda} for {self.supuesto}"


class GastosAdministrativos(models.Model):
    codigo = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=200)
    anio = models.PositiveIntegerField()
    mes = models.PositiveIntegerField(help_text="Mes (1-12)")
    total = models.DecimalField(max_digits=18, decimal_places=2)

    @property
    def promedio_mes(self):
        if self.mes and self.mes > 0:
            return self.total / Decimal(self.mes)
        return self.total

    def __str__(self):
        return f"Gasto {self.codigo} - {self.descripcion} ({self.anio}) - Mes: {self.mes}"


class CodigoContable(models.Model):
    codigo = models.CharField(max_length=20, unique=True, help_text="Código contable")
    nombre = models.CharField(max_length=200, help_text="Nombre o descripción asociada al código")

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
