# Generated by Django 5.0.1 on 2024-11-19 03:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('got', '0014_alter_equipmenthistory_date'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name='Overtime'),
            ],
        ),
    ]