# inventory_management/migrations/00XX_darbaja_migration.py
from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal
from got.paths import get_upload_path  # si lo necesitas para el campo ImageField
# Importa tu modelo Equipo si lo necesitas, o define a mano la ForeignKey

class Migration(migrations.Migration):

    initial = True  # O depende si es la primera migración que define DarBaja
                    # en inventory_management

    dependencies = [
        # Indica la dependencia con la migración de got
        # que "separó" DarBaja. 
        ('got', '0004_userprofile_station'), 
        # o la más reciente en got (donde se eliminó el modelo)
        # si la app inventory_management depende de got...
        # ... si no, ajusta la dependencia según tu caso.
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                # aquí no hacemos create table porque la tabla ya existe
                # y no queremos duplicarla, etc.
            ],
            state_operations=[
                # Añadimos el nuevo modelo en el "estado" de Django,
                # apuntando a la misma tabla (got_darbaja),
                # con managed=False.
                migrations.CreateModel(
                    name='DarBaja',
                    fields=[
                        ('id', models.BigAutoField(primary_key=True, serialize=False)),
                        (
                            'fecha',
                            models.DateField(auto_now_add=True)
                        ),
                        (
                            'reporter',
                            models.CharField(max_length=100)
                        ),
                        (
                            'responsable',
                            models.CharField(max_length=100)
                        ),
                        (
                            'activo',
                            models.CharField(max_length=150)
                        ),
                        (
                            'motivo',
                            models.CharField(
                                max_length=1,
                                choices=[
                                    ('o', 'Obsoleto'),
                                    ('r', 'Robo/Hurto'),
                                    ('p', 'Perdida'),
                                    ('i', 'Inservible/depreciado'),
                                ]
                            )
                        ),
                        ('observaciones', models.TextField()),
                        ('disposicion', models.TextField()),
                        (
                            'firma_responsable',
                            models.ImageField(upload_to=get_upload_path)
                        ),
                        (
                            'firma_autorizado',
                            models.ImageField(upload_to=get_upload_path)
                        ),
                        # La FK a Equipo → hay que referenciar 'got.Equipo' si no has movido Equipo:
                        (
                            'equipo',
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                to='got.equipo'
                            )
                        ),
                    ],
                    options={
                        'db_table': 'got_darbaja',  # la MISMA tabla 
                        'ordering': ['-fecha'],
                        'managed': False,          # no la manejes Django
                    },
                ),
            ]
        )
    ]
