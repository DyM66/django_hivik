# Generated by Django 5.0.1 on 2024-07-14 00:21

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('got', '0016_preoperacionaldiario_image_preoperacionaldiario'),
    ]

    operations = [
        migrations.AddField(
            model_name='preoperacional',
            name='vehiculo',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='got.equipo'),
        ),
        migrations.AddField(
            model_name='preoperacionaldiario',
            name='vehiculo',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='got.equipo'),
        ),
        migrations.AlterField(
            model_name='preoperacional',
            name='observaciones',
            field=models.TextField(blank=True, null=True),
        ),
    ]