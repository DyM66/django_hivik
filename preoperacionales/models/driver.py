from django.db import models


class Driver(models.Model):
    id_number = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    surname = models.CharField(max_length=100)

    class Meta:
        db_table = "preoperacionales_driver"
