# Generated by Django 5.0.1 on 2024-12-10 16:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('outbound', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='outbounddelivery',
            options={'ordering': ['-fecha'], 'permissions': (('can_approve_it', 'Aprobar salidas'),)},
        ),
        migrations.AlterField(
            model_name='outbounddelivery',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]