# Generated by Django 5.0.1 on 2024-10-14 18:31

import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('got', '0004_userprofile_station'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='cant_report_transf',
            field=models.DecimalField(blank=True, decimal_places=2, default=Decimal('0.00'), max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='transaction',
            name='suministro_transf',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='got.suministro'),
        ),
    ]