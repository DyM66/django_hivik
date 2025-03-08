# tic/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

def validate_title_word_count(value):
    if len(value.split()) > 100:
        raise ValidationError("El título no debe exceder 100 palabras.")

class Ticket(models.Model):
    TICKET_TYPE_CHOICES = [
        ('incidencia', 'Incidencia'),
        ('requerimiento', 'Requerimiento'),
    ]
    CATEGORY_CHOICES = [
        ('software', 'Software'),
        ('hardware', 'Hardware'),
    ]
    STATE_CHOICES = [
        ('abierto', 'Abierto'),
        ('en_proceso', 'En Proceso'),
        ('cerrado', 'Cerrado'),
    ]
    
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    title = models.CharField(max_length=255, validators=[validate_title_word_count])
    message = models.TextField()
    ticket_type = models.CharField(max_length=20, choices=TICKET_TYPE_CHOICES)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default='abierto')
    solution = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    taken_by = models.ForeignKey(User, null=True, blank=True, related_name='assigned_tickets', on_delete=models.SET_NULL)
    
    def __str__(self):
        return f"Ticket #{self.id} - {self.title} ({self.state})"
