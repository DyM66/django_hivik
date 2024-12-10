from django.db import migrations, models
import outbound.models

class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='OutboundDelivery',
                    fields=[
                        ('id', models.BigAutoField(primary_key=True, auto_created=True, serialize=False)),
                        ('destino', models.CharField(max_length=200)),
                        ('fecha', models.DateField(auto_now_add=True)),
                        ('motivo', models.TextField()),
                        ('propietario', models.CharField(max_length=100)),
                        ('responsable', models.CharField(max_length=100)),
                        ('recibe', models.CharField(max_length=100)),
                        ('vehiculo', models.CharField(max_length=100, null=True)),
                        ('auth', models.BooleanField(default=False)),
                        ('sign_recibe', models.ImageField(blank=True, null=True, upload_to=outbound.models.get_upload_path)),
                        ('adicional', models.TextField(blank=True, null=True)),
                    ],
                    options={
                        'db_table': 'got_salida',
                        'ordering': ['-fecha'],
                        'permissions': [('can_approve_it', 'Aprobar salidas')],
                    },
                ),
            ],
        ),
    ]
