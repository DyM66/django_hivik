from django.db import models
from django.utils import timezone
from got.paths import *

# Model 1: Registro de actividades
class ActivityLog(models.Model):
    user_name = models.CharField(max_length=100)
    action = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, null=True, blank=True)
    field_name = models.CharField(max_length=100, null=True, blank=True)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user_name} {self.action} {self.model_name} {self.field_name} at {self.timestamp}"