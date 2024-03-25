# Generated by Django 5.0.1 on 2024-03-23 16:47

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('got', '0013_ruta_equipo'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='historyhour',
            options={'ordering': ['-report_date']},
        ),
        migrations.AlterModelOptions(
            name='system',
            options={'ordering': ['asset__name', 'group']},
        ),
        migrations.RenameField(
            model_name='system',
            old_name='gruop',
            new_name='group',
        ),
        migrations.AddField(
            model_name='ruta',
            name='ot',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='got.ot'),
        ),
        migrations.AlterField(
            model_name='asset',
            name='area',
            field=models.CharField(choices=[('a', 'Motonave'), ('b', 'Buceo'), ('o', 'Oceanografia'), ('l', 'Locativo'), ('v', 'Vehiculos'), ('x', 'Apoyo')], default='a', max_length=1),
        ),
        migrations.AlterField(
            model_name='equipo',
            name='date_inv',
            field=models.DateField(),
        ),
        migrations.AlterField(
            model_name='equipo',
            name='system',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='equipos', to='got.system'),
        ),
        migrations.AlterField(
            model_name='equipo',
            name='tipo',
            field=models.CharField(choices=[('r', 'Rotativo'), ('nr', 'No rotativo')], default='nr', max_length=2),
        ),
        migrations.AlterField(
            model_name='ot',
            name='tipo_mtto',
            field=models.CharField(choices=[('p', 'Preventivo'), ('c', 'Correctivo'), ('m', 'Modificativo')], max_length=50),
        ),
        migrations.AlterField(
            model_name='ruta',
            name='control',
            field=models.CharField(choices=[('d', 'Días'), ('h', 'Horas')], max_length=50),
        ),
        migrations.AlterField(
            model_name='ruta',
            name='name',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name='system',
            name='state',
            field=models.CharField(choices=[('m', 'Mantenimiento'), ('o', 'Operativo'), ('x', 'Fuera de servicio')], default='m', max_length=1),
        ),
    ]