from django.db import models
from django.contrib.auth.models import User
from datetime import datetime
import uuid

# Funciones auxiliares
def get_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"media/{datetime.now():%Y%m%d%H%M%S}-{uuid.uuid4()}.{ext}"
    return filename

# Model 2: Carasteristicas del usuario
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    cargo = models.CharField(max_length=100, null=True, blank=True)
    firma = models.ImageField(upload_to=get_upload_path, null=True, blank=True)
    station = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s profile"