from django import forms
from .models import DarBaja

class DarBajaForm(forms.ModelForm):
    class Meta:
        model = DarBaja
        fields = ['motivo', 'observaciones', 'disposicion', 'responsable']
        widgets = {
            'motivo': forms.Select(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control'}),
            'disposicion': forms.Textarea(attrs={'class': 'form-control'}),
            'responsable': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'motivo': 'Motivo de la baja',
            'observaciones': 'Observaciones',
            'disposicion': 'Disposición final del equipo',
            'responsable': 'Responsable del equipo',
        }