from django.db import migrations, models
import outbound.models
import django.db.models.deletion
import django.core.validators

class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Place',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, unique=True)),
                ('latitude', models.DecimalField(blank=True, decimal_places=6, help_text='Latitud de la ubicación.', max_digits=9, null=True)),
                ('longitude', models.DecimalField(blank=True, decimal_places=6, help_text='Longitude de la ubicación.', max_digits=9, null=True)),
                ('city', models.CharField(blank=True, max_length=100, null=True)),
                ('contact_person', models.CharField(blank=True, max_length=100, null=True)),
                ('contact_phone', models.CharField(blank=True, max_length=15, null=True, validators=[django.core.validators.RegexValidator(message='Número de teléfono inválido.', regex='^\\+?1?\\d{9,15}$')])),
            ],
            options={
                'verbose_name': 'Lugar',
                'verbose_name_plural': 'Lugares',
                'db_table': 'outbound_place',
            },
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='OutboundDelivery',
                    fields=[
                        ('id', models.BigAutoField(primary_key=True, auto_created=True, serialize=False)),
                        ('destino', models.CharField(blank=True, max_length=200, null=True)),
                        ('destination', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='outbound_deliveries', to='outbound.place')),
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
