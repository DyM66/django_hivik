# Generated by Django 5.0.1 on 2024-10-07 04:07

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('got', '0005_activitylog_delete_location_asset_modified_by_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ot',
            name='super',
        ),
        migrations.AlterField(
            model_name='darbaja',
            name='activo',
            field=models.CharField(max_length=150),
        ),
        migrations.CreateModel(
            name='Requirement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('approved', models.BooleanField(default=False)),
                ('operation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='got.operation')),
            ],
        ),
    ]