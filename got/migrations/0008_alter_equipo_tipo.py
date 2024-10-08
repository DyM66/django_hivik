# Generated by Django 5.0.1 on 2024-10-07 20:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('got', '0007_equipo_recomendaciones'),
    ]

    operations = [
        migrations.AlterField(
            model_name='equipo',
            name='tipo',
            field=models.CharField(choices=[('a', 'Climatización'), ('b', 'Bomba'), ('c', 'Compresor'), ('d', 'Grúa'), ('e', 'Motor eléctrico'), ('f', 'Emergencias'), ('g', 'Generador'), ('h', 'Cilindro hidráulico'), ('i', 'Instrumentos y herramientas'), ('j', 'Distribución eléctrica'), ('k', 'Tanque de almacenamiento'), ('l', 'Gobierno'), ('m', 'Comunicación'), ('n', 'Navegación'), ('o', 'Maniobras'), ('nr', 'No rotativo'), ('r', 'Motor a combustión'), ('t', 'Transmisión'), ('u', 'Unidad Hidráulica'), ('v', 'Valvula'), ('w', 'Winche'), ('x', 'Estructuras'), ('y', 'Soporte de vida'), ('z', 'Banco de baterias')], default='nr', max_length=2),
        ),
    ]
