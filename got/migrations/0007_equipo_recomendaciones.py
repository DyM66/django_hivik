# Generated by Django 5.0.1 on 2024-10-07 16:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('got', '0006_remove_ot_super_alter_darbaja_activo_requirement_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='equipo',
            name='recomendaciones',
            field=models.TextField(blank=True, null=True),
        ),
    ]
