# Generated by Django 5.0.1 on 2025-04-09 11:42

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inv', '0002_retiredsupplyimage'),
    ]

    operations = [
        migrations.AddField(
            model_name='retiredsupply',
            name='transaction',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='retired_supply', to='inv.transaction'),
        ),
    ]
