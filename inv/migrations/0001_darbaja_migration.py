# inventory_management/migrations/00XX_darbaja_migration.py
from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal
from got.paths import get_upload_path

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('got', '0003_remove_task_ruta_delete_ruta'), 
    ]

    operations = [
        migrations.CreateModel(
            name='Transferencia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField(auto_now_add=True)),
                ('responsable', models.CharField(max_length=100)),
                ('observaciones', models.TextField(blank=True, null=True)),
                ('destino', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='destino', to='got.system')),
                ('equipo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='got.equipo')),
                ('origen', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='origen', to='got.system')),
            ],
            options={
                'db_table': 'got_transferencia',
                'ordering': ['-fecha'],
            },
        ),
        migrations.CreateModel(
            name='DarBaja',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('fecha', models.DateField(auto_now_add=True)),
                ('reporter', models.CharField(max_length=100)),
                ('responsable', models.CharField(max_length=100)),
                ('activo', models.CharField(max_length=150)),
                ('motivo', models.CharField(max_length=1, choices=[('o', 'Obsoleto'), ('r', 'Robo/Hurto'), ('p', 'Perdida'), ('i', 'Inservible/depreciado'),])),
                ('observaciones', models.TextField()),
                ('disposicion', models.TextField()),
                ('firma_responsable', models.ImageField(upload_to=get_upload_path)),
                ('firma_autorizado', models.ImageField(upload_to=get_upload_path)),
                ('equipo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='got.equipo')),
            ],
            options={
                'db_table': 'got_darbaja',  # la MISMA tabla 
                'ordering': ['-fecha'],
                'managed': False,          # no la manejes Django
            },
        ),
        migrations.CreateModel(
            name='EquipoCodeCounter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('asset_abbr', models.CharField(max_length=50)),
                ('tipo', models.CharField(max_length=2)),
                ('last_seq', models.PositiveIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Contador de Código de Equipo',
                'verbose_name_plural': 'Contadores de Código de Equipo',
                'unique_together': {('asset_abbr', 'tipo')},
            },
        ),
    ]
