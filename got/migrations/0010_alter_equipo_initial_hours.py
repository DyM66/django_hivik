# Generated by Django 5.0.1 on 2024-03-16 03:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('got', '0009_equipo_initial_hours_ruta_control'),
    ]

    operations = [
        migrations.AlterField(
            model_name='equipo',
            name='initial_hours',
            field=models.IntegerField(default=0),
        ),
    ]