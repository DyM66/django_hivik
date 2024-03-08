# Generated by Django 5.0.1 on 2024-03-08 01:53

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('got', '0007_alter_asset_calado_maximo_alter_asset_eslora_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='equipo',
            name='location',
        ),
        migrations.RemoveField(
            model_name='equipo',
            name='state',
        ),
        migrations.RemoveField(
            model_name='ruta',
            name='name',
        ),
        migrations.AddField(
            model_name='system',
            name='location',
            field=models.CharField(blank=True, default='Cartagena', max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='system',
            name='state',
            field=models.CharField(choices=[('m', 'Mantenimiento'), ('o', 'Operativo'), ('x', 'Fuera de servicio')], default='m', max_length=50),
        ),
        migrations.AlterField(
            model_name='equipo',
            name='system',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='components', to='got.system'),
        ),
    ]