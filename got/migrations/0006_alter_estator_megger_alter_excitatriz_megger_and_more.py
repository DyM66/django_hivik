# Generated by Django 5.0.1 on 2024-06-18 18:32

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('got', '0005_remove_megger_fecha_alter_equipo_tipo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='estator',
            name='megger',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='got.megger'),
        ),
        migrations.AlterField(
            model_name='excitatriz',
            name='megger',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='got.megger'),
        ),
        migrations.AlterField(
            model_name='rodamientosescudos',
            name='megger',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='got.megger'),
        ),
        migrations.AlterField(
            model_name='rotoraux',
            name='megger',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='got.megger'),
        ),
        migrations.AlterField(
            model_name='rotormain',
            name='megger',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='got.megger'),
        ),
    ]
