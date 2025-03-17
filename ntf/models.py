# ntf/models.py
from django.db import models
from django.contrib.auth.models import User

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=100, blank=True) 
    message = models.TextField()
    redirect_url = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    seen = models.BooleanField(default=False)

    class Meta:
        db_table = 'got_notification'

    def __str__(self):
        return f"Notificación para {self.user.username}: {self.message[:50]}"
