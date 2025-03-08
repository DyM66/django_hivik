# tic/forms.py
from django import forms
from .models import Ticket

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['title', 'ticket_type', 'category', 'message']
        labels = {
            'title': 'Motivo',
            'ticket_type': 'Tipo de ticket',
            'category': 'Categoria',
            'message': 'Decripción'
        }
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Título (máximo 100 palabras)'
            }),
            'ticket_type': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={
                'class': 'form-control', 
                'placeholder': 'Describe la incidencia o requerimiento'
            }),
        }
