# outbound/forms.py
from django import forms
from .models import *

class SalidaForm(forms.ModelForm):
    class Meta:
        model = OutboundDelivery
        fields = ['destino', 'motivo', 'recibe', 'vehiculo', 'propietario', 'adicional']
        labels = {
            'destino': 'Dirección de destino',
            'motivo': 'Justificación de la salida',
            'recibe': 'Transportado por',
            'vehiculo': 'Matricula del vehiculo',
            'propietario': 'Propietario',
            'adicional': 'Información adicional'
        }
        widgets = {
            'destino': forms.TextInput(attrs={'class': 'form-control'}),
            'motivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'recibe': forms.TextInput(attrs={'class': 'form-control'}),
            'vehiculo': forms.TextInput(attrs={'class': 'form-control'}),
            'propietario': forms.TextInput(attrs={'class': 'form-control'}),
            'adicional': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class PlaceForm(forms.ModelForm):
    class Meta:
        model = Place
        fields = ['name', 'latitude', 'longitude', 'contact_person', 'contact_phone']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'latitude': 'Selecciona la ubicación en el mapa para obtener las coordenadas.',
            'longitude': 'Selecciona la ubicación en el mapa para obtener las coordenadas.',
        }