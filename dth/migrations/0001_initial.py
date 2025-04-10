# Generated by Django 5.0.1 on 2025-02-01 23:53
import got.paths
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import got.models
from decimal import Decimal
import uuid
import dth.models.docs_requests

class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cargo', models.CharField(blank=True, max_length=100, null=True)),
                ('firma', models.ImageField(blank=True, null=True, upload_to=got.models.get_upload_path)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AlterModelTable(
            name='userprofile',
            table='got_userprofile',
        ),
        migrations.CreateModel(
            name='OvertimeProject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('description', models.TextField()),
                ('asset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='got.asset')),
                ('reported_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('report_date', models.DateField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Overtime',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start', models.TimeField()),
                ('end', models.TimeField()),
                ('remarks', models.TextField(blank=True, null=True)),
                ('nombre_completo', models.CharField(blank=True, default='', max_length=200, null=True)),
                ('cedula', models.CharField(blank=True, default='', max_length=20, null=True)),
                ('cargo', models.CharField(blank=True, choices=[('a', 'Capitán'), ('b', 'Primer Oficial de Puente'), ('c', 'Marino'), ('d', 'Jefe de Máquinas'), ('e', 'Primer Oficial de Máquinas'), ('f', 'Maquinista'), ('g', 'Otro')], max_length=1, null=True)),
                ('project', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='dth.overtimeproject')),
                ('state', models.CharField(choices=[('a', 'Aprobado'), ('b', 'No aprobado'), ('c', 'Pendiente')], default='c', max_length=1)),
                ('worker', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='dth.nomina')),
            ],
            options={
                'db_table': 'got_overtime',
                'permissions': [('can_approve_overtime', 'Puede aprobar horas extras')],
            },
        ),
        migrations.CreateModel(
            name='Nomina',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('id_number', models.CharField(help_text='Identificación del empleado.', max_length=50, verbose_name='Número de documento')),
                ('name', models.CharField(help_text='Nombres', max_length=100)),
                ('surname', models.CharField(help_text='Apellidos', max_length=100)),
                ('position', models.CharField(help_text='Cargo o puesto.', max_length=100)),
                ('salary', models.DecimalField(decimal_places=2, help_text='Salario en COP.', max_digits=18)),
                ('admission', models.DateField(help_text='Fecha de ingreso del empleado. (Obligatoria)')),
                ('expiration', models.DateField(blank=True, help_text='Fecha de expiración del contrato, si aplica.', null=True)),
                ('risk_class', models.CharField(blank=True, choices=[('I', '0.522%'), ('II', '1.044%'), ('III', '2.436%'), ('IV', '4.350%'), ('V', '6.96%')], help_text='Clase de riesgo laboral.', max_length=3, null=True)), 
                ('is_driver', models.BooleanField(default=False)),
                ('gender', models.CharField(choices=[('h', 'Hombre'), ('m', 'Mujer')], default='h', max_length=1)),
                ('photo', models.ImageField(blank=True, help_text='Fotografía del empleado.', null=True, upload_to=got.paths.get_upload_path)),
                ('position_id', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='employees', to='dth.position')),
                ('email', models.EmailField(blank=True, help_text='Correo electrónico del empleado.', max_length=254, null=True)),
                ('employment_status', models.CharField(choices=[('a', 'Activo'), ('r', 'Retirado'), ('l', 'Licencia'), ('s', 'Suspendido'), ('i', 'Incapacitado')], default='a', help_text='Estado actual del empleado en la empresa.', max_length=1)),
                ('phone', models.CharField(blank=True, help_text='Teléfono de contacto.', max_length=50, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='NominaReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mes', models.PositiveSmallIntegerField(help_text='Mes (1-12).')),
                ('anio', models.PositiveSmallIntegerField(help_text='Año.')),
                ('dv01', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Sueldo básico.', max_digits=18)),
                ('dv25', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Pago Vacaciones', max_digits=18)),
                ('dv03', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Subsidio de transporte', max_digits=18)),
                ('dv103', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Licencia de la familia', max_digits=18)),
                ('dv27', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Intereses de cesantías año anterior.', max_digits=18)),
                ('dv30', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Cesantías.', max_digits=18)),
                ('dx03', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Pensión.', max_digits=18)),
                ('dx05', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Solidaridad.', max_digits=18)),
                ('dx01', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Retención en la fuente.', max_digits=18)),
                ('dx07', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Exequias Lordoy.', max_digits=18)),
                ('dx12', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Descuento pensión voluntaria.', max_digits=18)),
                ('dx63', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Banco de Occidente.', max_digits=18)),
                ('dx64', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Confenalco.', max_digits=18)),
                ('dx66', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Préstamo empleado.', max_digits=18)),
                ('nomina', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reportes', to='dth.nomina')),
                ('current_salary', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Salario Actual', max_digits=18)),
            ],
        ),
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='EmployeeDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to=dth.models.positions.get_upload_path_employee)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('expiration_date', models.DateField(blank=True, null=True)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dth.document')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='employee_documents', to='dth.nomina')),
            ],
            options={
                'unique_together': {('employee', 'document')},
            },
        ),
        migrations.CreateModel(
            name='PositionDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mandatory', models.BooleanField(default=True)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='document_positions', to='dth.document')),
                ('position', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='position_documents', to='dth.position')),
            ],
            options={
                'unique_together': {('position', 'document')},
            },
        ),
        migrations.CreateModel(
            name='Position',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('category', models.CharField(blank=True, choices=[('o', 'Operativo'), ('a', 'Administrativo'), ('m', 'Mixto')], max_length=1, null=True)),
                ('rule', models.CharField(blank=True, max_length=100, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='DocumentRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('token', models.CharField(max_length=40, unique=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='requests', to='dth.nomina')),
            ],
        ),
        migrations.CreateModel(
            name='DocumentRequestItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pdf_file', models.FileField(blank=True, null=True, upload_to=dth.models.docs_requests.get_upload_path_temp)),
                ('expiration_date', models.DateField(blank=True, null=True)),
                ('approved', models.BooleanField(default=False)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dth.document')),
                ('request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='dth.documentrequest')),
                ('verified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('rejection_reason', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[('P', 'Pendiente'), ('A', 'Aprobado'), ('R', 'Rechazado')], default='P', max_length=1)),
            ],
        ),
        migrations.CreateModel(
            name='EPS',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
        ),
    ]
