# Generated by Django 5.0.1 on 2024-06-23 23:47

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('got', '0008_consumibles_control_stock'),
    ]

    operations = [
        migrations.AddField(
            model_name='consumibles',
            name='control',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='got.control'),
        ),
        migrations.AlterUniqueTogether(
            name='stock',
            unique_together={('item', 'asset')},
        ),
    ]