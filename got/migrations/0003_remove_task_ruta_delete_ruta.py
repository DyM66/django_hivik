# Generated by Django 5.0.1 on 2024-03-08 04:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('got', '0002_ruta_task_ruta'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='task',
            name='ruta',
        ),
        migrations.DeleteModel(
            name='Ruta',
        ),
    ]
