# Generated by Django 5.0.1 on 2024-06-05 19:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('got', '0010_document_tasks_megger_excitatriz_estator_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='solicitud',
            name='seccion',
            field=models.CharField(choices=[('c', 'Consumibles'), ('h', 'Herramientas'), ('r', 'Repuestos')], default='c', max_length=1),
        ),
    ]