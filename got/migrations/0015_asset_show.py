# Generated by Django 5.0.1 on 2024-11-22 05:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('got', '0014_alter_equipmenthistory_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='asset',
            name='show',
            field=models.BooleanField(default=True),
        ),
    ]