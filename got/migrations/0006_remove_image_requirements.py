# Generated by Django 5.0.1 on 2025-03-03 09:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('got', '0005_ot_closing_date'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='image',
            name='requirements',
        ),
    ]
