# outbound/forms.py
from django import forms
from .models import *

class SalidaForm(forms.ModelForm):
    class Meta:
        model = OutboundDelivery
        fields = ['destination', 'motivo', 'recibe', 'vehiculo', 'propietario', 'adicional']
        labels = {
            'destination': 'Dirección de destino',
            'motivo': 'Justificación de la salida',
            'recibe': 'Transportado por',
            'vehiculo': 'Matricula del vehiculo',
            'propietario': 'Propietario',
            'adicional': 'Información adicional'
        }
        widgets = {
            'destination': forms.HiddenInput(),
            'motivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'recibe': forms.TextInput(attrs={'class': 'form-control'}),
            'vehiculo': forms.TextInput(attrs={'class': 'form-control'}),
            'propietario': forms.TextInput(attrs={'class': 'form-control'}),
            'adicional': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super(SalidaForm, self).__init__(*args, **kwargs)
        # Personalizar el queryset si es necesario
        self.fields['destination'].queryset = Place.objects.all()
        self.fields['destination'].required = True  # Hacerlo obligatorio


class PlaceForm(forms.ModelForm):
    class Meta:
        model = Place
        fields = ['name', 'latitude', 'longitude', 'city', 'contact_person', 'contact_phone']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
        }
        help_texts = {
            'latitude': 'Selecciona la ubicación en el mapa o ingresa las coordenadas manualmente.',
            'longitude': 'Selecciona la ubicación en el mapa o ingresa las coordenadas manualmente.',
            'city': 'Nombre de la ciudad obtenida automáticamente.',
        }

    def clean_latitude(self):
        lat = self.cleaned_data.get('latitude')
        if lat is not None:
            if not (-90 <= lat <= 90):
                raise forms.ValidationError('La latitud debe estar entre -90 y 90 grados.')
        return lat

    def clean_longitude(self):
        lng = self.cleaned_data.get('longitude')
        if lng is not None:
            if not (-180 <= lng <= 180):
                raise forms.ValidationError('La longitud debe estar entre -180 y 180 grados.')
        return lng