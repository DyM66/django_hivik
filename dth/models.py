from django.db import models
from django.contrib.auth.models import User
from got.paths import get_upload_path  # Puedes copiar o reutilizar la función get_upload_path

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    cargo = models.CharField(max_length=100, null=True, blank=True)
    firma = models.ImageField(upload_to=get_upload_path, null=True, blank=True)
    dpto = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        # Es muy importante conservar el mismo nombre de tabla para que Django no intente crear una nueva.
        db_table = 'got_userprofile'
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"

    def __str__(self):
        return f"{self.user.username}'s profile"
