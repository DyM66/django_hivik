# Generated by Django 5.0.1 on 2024-07-14 17:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('got', '0019_alter_preoperacionaldiario_combustible_level'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='preoperacionaldiario',
            name='conexiones',
        ),
        migrations.RemoveField(
            model_name='preoperacionaldiario',
            name='extintor',
        ),
        migrations.RemoveField(
            model_name='preoperacionaldiario',
            name='llanta_repuesto',
        ),
        migrations.AddField(
            model_name='preoperacionaldiario',
            name='llantas',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='aceite_level',
            field=models.CharField(choices=[('b', 'Bajo'), ('m', 'Medio'), ('l', 'Lleno')], default='l', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='acoples',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='aire',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='alarma_retroceso',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='alternador',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='apoyacabezas',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='arranque',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='asiento',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='bateria',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='bujes',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='caja_cambios',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='chapas',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='cinturon',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='cocuyos',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='correas',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='cruceta',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='direccion',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='ejes',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='elevavidrios',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='esparragos',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='espejos',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='freno_seguridad',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='freno_servicio',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='hidraulic_level',
            field=models.CharField(choices=[('b', 'Bajo'), ('m', 'Medio'), ('l', 'Lleno')], default='l', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='liq_frenos_level',
            field=models.CharField(choices=[('b', 'Bajo'), ('m', 'Medio'), ('l', 'Lleno')], default='l', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='luces_altas',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='luces_direccionales',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='luces_medias',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='lunas',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='luz_interna',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='luz_placa',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='mangueras',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='manijas',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='pito',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='poleas',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='puertas',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='radiador',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='refrigerante_level',
            field=models.CharField(choices=[('b', 'Bajo'), ('m', 'Medio'), ('l', 'Lleno')], default='l', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='rines',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='rotulas',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='suspencion',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='tanques',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='terminales',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='tuercas',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
        migrations.AlterField(
            model_name='preoperacionaldiario',
            name='vidrio_panoramico',
            field=models.CharField(choices=[('b', 'Bueno'), ('r', 'Regular'), ('m', 'Malo')], default='b', max_length=1),
        ),
    ]