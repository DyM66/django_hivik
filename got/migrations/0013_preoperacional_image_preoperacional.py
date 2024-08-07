# Generated by Django 5.0.1 on 2024-07-09 21:19

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('got', '0012_remove_control_asset_remove_control_reporter_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Preoperacional',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField(auto_now_add=True)),
                ('cedula', models.CharField(max_length=20)),
                ('motivo', models.TextField()),
                ('salida', models.CharField(max_length=150)),
                ('destino', models.CharField(max_length=150)),
                ('tipo_ruta', models.CharField(choices=[('u', 'Urbana'), ('r', 'Rural'), ('m', 'Mixta (Urbana y Rural)')], max_length=1)),
                ('autorizado', models.CharField(choices=[('a', 'Alejandro Angel/ Deliana Lacayo/ Jenny Castillo - Dpto. abasteciiento y logistica'), ('b', 'Juan Pablo Llanos - Residente Santa Marta'), ('c', 'Jose Jurado/ Julieth Ximena - Residente Tumaco'), ('d', 'Issis Alvarez - Directora Administrativa'), ('e', 'Jennifer Padilla - Gerente administrativa'), ('f', 'German Locarno - Gerente de operaciones'), ('g', 'Alexander Davey - Gerente de mantenimiento'), ('h', 'Carlos Cortés - Subgerente'), ('i', 'Federico Payan - Gerente Financiero'), ('j', 'Diego Lievano - Jefe de buceo'), ('k', 'Klaus Bartel - Gerente General')], max_length=1)),
                ('kilometraje', models.IntegerField()),
                ('observaciones', models.TextField(blank=True, null=True)),
                ('reporter', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('agua', models.BooleanField()),
                ('condiciones', models.BooleanField()),
                ('control', models.BooleanField()),
                ('dormido', models.BooleanField()),
                ('enfermo', models.BooleanField()),
                ('horas_trabajo', models.BooleanField()),
                ('medicamentos', models.BooleanField()),
                ('molestias', models.BooleanField()),
                ('radio_aire', models.BooleanField()),
                ('sueño', models.BooleanField()),
                ('vehiculo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='got.equipo')),
                ('nombre_no_registrado', models.CharField(blank=True, max_length=100, null=True)),
            ],
            options={'ordering': ['-fecha']},
        ),
        migrations.AddField(
            model_name='image',
            name='preoperacional',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='images', to='got.preoperacional'),
        ),
    ]
