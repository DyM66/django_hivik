# inventory_management/migrations/00XX_darbaja_migration.py
from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal
from got.paths import get_upload_path
from django.conf import settings
import got.paths

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('got', '0002_ruta_task_ruta'), 
    ]

    operations = [
        migrations.CreateModel(
            name='Transference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField(auto_now_add=True)),
                ('responsable', models.CharField(max_length=150)),
                ('observaciones', models.TextField(blank=True, null=True)),
                ('destino', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='destino', to='got.system')),
                ('equipo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='got.equipo')),
                ('origen', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='origen', to='got.system')),
                ('receptor', models.CharField(max_length=150)),
                ('signature', models.ImageField(help_text='Firma obligatoria en formato de imagen (jpg, png, etc.)', upload_to='transference_signatures/')),
            ],
            options={
                'ordering': ['-fecha'],
            },
        ),
        migrations.CreateModel(
            name='DarBaja',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField(auto_now_add=True)),
                ('reporter', models.CharField(max_length=100)),
                ('responsable', models.CharField(max_length=100)),
                ('activo', models.CharField(max_length=150)),
                ('motivo', models.CharField(choices=[('o', 'Obsoleto'), ('r', 'Robo/Hurto'), ('p', 'Perdida'), ('i', 'Inservible/depreciado'), ('v', 'Venta')], max_length=1)),
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
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cant', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10)),
                ('fecha', models.DateField()),
                ('user', models.CharField(max_length=100)),
                ('motivo', models.TextField(blank=True, null=True)),
                ('tipo', models.CharField(choices=[('i', 'Ingreso'), ('c', 'Consumo'), ('t', 'Transferencia'), ('e', 'Ingreso externo')], default='i', max_length=1)),
                ('cant_report', models.DecimalField(blank=True, decimal_places=2, default=Decimal('0.00'), max_digits=10, null=True)),
                ('cant_report_transf', models.DecimalField(blank=True, decimal_places=2, default=Decimal('0.00'), max_digits=10, null=True)),
                ('suministro', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transacciones', to='inv.suministro')),
                ('suministro_transf', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='inv.suministro')),
            ],
            options={
                'permissions': (('can_add_supply', 'Puede añadir suministros'),),
            },
        ),
        migrations.AddConstraint(
            model_name='transaction',
            constraint=models.UniqueConstraint(fields=('suministro', 'fecha', 'tipo'), name='unique_suministro_fecha_tipo'),
        ),
        migrations.CreateModel(
            name='Solicitud',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('suministros', models.TextField()),
                ('approved', models.BooleanField(default=False)),
                ('asset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='got.asset')),
                ('ot', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='got.ot')),
                ('solicitante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('num_sc', models.TextField(blank=True, null=True)),
                ('approval_date', models.DateTimeField(blank=True, null=True)),
                ('sc_change_date', models.DateTimeField(blank=True, null=True)),
                ('cancel', models.BooleanField(default=False)),
                ('cancel_reason', models.TextField(blank=True, null=True)),
                ('cancel_date', models.DateTimeField(blank=True, null=True)),
                ('approved_by', models.CharField(blank=True, max_length=100, null=True)),
                ('recibido_por', models.TextField(blank=True, null=True)),
                ('satisfaccion', models.BooleanField(default=False)),
                ('requested_by', models.CharField(blank=True, max_length=100, null=True)),
                ('dpto', models.CharField(choices=[('m', 'Mantenimiento'), ('o', 'Operaciones')], default='m', max_length=1)),
                ('quotation', models.CharField(blank=True, max_length=200, null=True)),
                ('quotation_file', models.FileField(blank=True, null=True, upload_to=got.paths.get_upload_pdfs)),
                ('total', models.DecimalField(decimal_places=2, default=0.0, max_digits=18)),
            ],
            options={
                'db_table': 'got_solicitud',
                'ordering': ['-creation_date'],
                'permissions': (
                    ('can_approve', 'Aprobar solicitudes'),
                    ('can_cancel', 'Puede cancelar'),
                    ('can_view_all_rqs', 'Puede ver todas las solicitudes'), 
                    ('can_transfer_solicitud', 'Puede transferir solicitudes'),
                ),
            },
        ),
        migrations.CreateModel(
            name='Suministro',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10)),
                ('Solicitud', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='inv.solicitud')),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='got.item')),
                ('equipo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='suministros', to='got.equipo'),),
                ('asset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='suministros', to='got.asset')),
            ],
        ),
    ]


        #    migrations.RunSQL(
        #     """
        #     UPDATE django_content_type
        #     SET app_label = 'inv'
        #     WHERE app_label = 'got' AND model = 'solicitud';
        #     """,
        #     reverse_sql="""
        #     UPDATE django_content_type
        #     SET app_label = 'got'
        #     WHERE app_label = 'inv' AND model = 'solicitud';
        #     """
        # ),