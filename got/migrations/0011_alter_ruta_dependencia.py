# Generated by Django 5.0.1 on 2024-06-29 15:26

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('got', '0010_alter_equipo_date_inv_alter_estator_pf_10min_l1_l2_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ruta',
            name='dependencia',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dependiente', to='got.ruta'),
        ),
    ]
