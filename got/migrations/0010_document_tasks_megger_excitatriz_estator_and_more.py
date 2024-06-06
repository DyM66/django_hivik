# Generated by Django 5.0.1 on 2024-06-05 18:56

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('got', '0009_alter_task_options'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='tasks',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='documents', to='got.task'),
        ),
        migrations.CreateModel(
            name='Megger',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField()),
                ('equipo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='got.equipo')),
                ('ot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='got.ot')),
            ],
        ),
        migrations.CreateModel(
            name='Excitatriz',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pi_1min_l_tierra', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pi_10min_l_tierra', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pi_obs_l_tierra', models.TextField(blank=True, null=True)),
                ('pf_1min_l_tierra', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pf_10min_l_tierra', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pf_obs_l_tierra', models.TextField(blank=True, null=True)),
                ('megger', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='got.megger')),
            ],
        ),
        migrations.CreateModel(
            name='Estator',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pi_1min_l1_tierra', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pi_1min_l2_tierra', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pi_1min_l3_tierra', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pi_1min_l1_l2', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pi_1min_l2_l3', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pi_1min_l3_l1', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pi_10min_l1_tierra', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pi_10min_l2_tierra', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pi_10min_l3_tierra', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pi_10min_l1_l2', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pi_10min_l2_l3', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pi_10min_l3_l1', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pi_obs_l1_tierra', models.TextField(blank=True, null=True)),
                ('pi_obs_l2_tierra', models.TextField(blank=True, null=True)),
                ('pi_obs_l3_tierra', models.TextField(blank=True, null=True)),
                ('pi_obs_l1_l2', models.TextField(blank=True, null=True)),
                ('pi_obs_l2_l3', models.TextField(blank=True, null=True)),
                ('pi_obs_l3_l1', models.TextField(blank=True, null=True)),
                ('pf_1min_l1_tierra', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pf_1min_l2_tierra', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pf_1min_l3_tierra', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pf_1min_l1_l2', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pf_1min_l2_l3', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pf_1min_l3_l1', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pf_10min_l1_tierra', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pf_10min_l2_tierra', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pf_10min_l3_tierra', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pf_10min_l1_l2', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pf_10min_l2_l3', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pf_10min_l3_l1', models.DecimalField(blank=True, decimal_places=4, max_digits=8, null=True)),
                ('pf_obs_l1_tierra', models.TextField(blank=True, null=True)),
                ('pf_obs_l2_tierra', models.TextField(blank=True, null=True)),
                ('pf_obs_l3_tierra', models.TextField(blank=True, null=True)),
                ('pf_obs_l1_l2', models.TextField(blank=True, null=True)),
                ('pf_obs_l2_l3', models.TextField(blank=True, null=True)),
                ('pf_obs_l3_l1', models.TextField(blank=True, null=True)),
                ('megger', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='got.megger')),
            ],
        ),
        migrations.CreateModel(
            name='RodamientosEscudos',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rodamientoas', models.TextField(blank=True, null=True)),
                ('rodamientobs', models.TextField(blank=True, null=True)),
                ('escudoas', models.TextField(blank=True, null=True)),
                ('escudobs', models.TextField(blank=True, null=True)),
                ('megger', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='got.megger')),
            ],
        ),
        migrations.CreateModel(
            name='RotorAux',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pi_1min_l_tierra', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('pi_10min_l_tierra', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('pi_obs_l_tierra', models.TextField(blank=True, null=True)),
                ('pf_1min_l_tierra', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('pf_10min_l_tierra', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('pf_obs_l_tierra', models.TextField(blank=True, null=True)),
                ('megger', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='got.megger')),
            ],
        ),
        migrations.CreateModel(
            name='RotorMain',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pi_1min_l_tierra', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('pi_10min_l_tierra', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('pi_obs_l_tierra', models.TextField(blank=True, null=True)),
                ('pf_1min_l_tierra', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('pf_10min_l_tierra', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('pf_obs_l_tierra', models.TextField(blank=True, null=True)),
                ('megger', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='got.megger')),
            ],
        ),
        migrations.CreateModel(
            name='Solicitud',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_date', models.DateField(auto_now_add=True)),
                ('seccion', models.CharField(choices=[('c', 'Consumibles'), ('h', 'Herramientas'), ('r', 'Repuestos')], max_length=1)),
                ('suministros', models.TextField()),
                ('approved', models.BooleanField(default=False)),
                ('asset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='got.asset')),
                ('ot', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='got.ot')),
                ('solicitante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]