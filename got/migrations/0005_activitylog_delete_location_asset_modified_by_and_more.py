# Generated by Django 5.0.1 on 2024-09-09 12:46

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('got', '0004_userprofile_station'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ActivityLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_name', models.CharField(max_length=100)),
                ('action', models.CharField(max_length=100)),
                ('model_name', models.CharField(max_length=100)),
                ('object_id', models.CharField(blank=True, max_length=100, null=True)),
                ('field_name', models.CharField(blank=True, max_length=100, null=True)),
                ('old_value', models.TextField(blank=True, null=True)),
                ('new_value', models.TextField(blank=True, null=True)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.DeleteModel(
            name='Location',
        ),
        migrations.AddField(
            model_name='asset',
            name='modified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='modified_assets', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='equipo',
            name='modified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='failurereport',
            name='modified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='modified_failures', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historyhour',
            name='modified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='modified_hours', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='item',
            name='modified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='ot',
            name='modified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='modified_ots', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='ruta',
            name='modified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='solicitud',
            name='modified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='modified_solicitudes', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='system',
            name='modified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='task',
            name='modified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='modified_tasks', to=settings.AUTH_USER_MODEL),
        ),
    ]