# Generated by Django 5.0.1 on 2024-11-19 03:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('overtime', '0001_move_overtime_from_got'),
    ]

    operations = [
        migrations.AlterField(
            model_name='overtime',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
