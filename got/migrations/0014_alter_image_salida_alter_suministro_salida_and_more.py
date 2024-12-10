
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('got', '0013_remove_task_evidence_equipmenthistory'),
        ('outbound', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='image',
            name='salida',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='images', to='outbound.outbounddelivery'),
        ),
        migrations.AlterField(
            model_name='suministro',
            name='salida',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='suministros', to='outbound.outbounddelivery'),
        ),
    ]
