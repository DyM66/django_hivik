# Generated by Django 5.0.1 on 2025-04-05 12:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dth', '0003_remove_userprofile_dpto_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='nomina',
            name='employment_status',
            field=models.CharField(choices=[('a', 'Activo'), ('r', 'Retirado'), ('l', 'Licencia'), ('s', 'Suspendido'), ('i', 'Incapacitado')], default='a', help_text='Estado actual del empleado en la empresa.', max_length=1),
        ),
    ]
