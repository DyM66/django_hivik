# mto/forms.py
from django import forms
from inv.models import Solicitud

class SolicitudUpdateForm(forms.ModelForm):
    class Meta:
        model = Solicitud
        fields = ['quotation', 'quotation_file', 'total', 'recibido_por']
        labels = {

            'quotation': 'Cotización',  # Se mostrará "Estado" en lugar de "recibido_por"
            'quotation_file': 'Cotización',  # Se mostrará "Estado" en lugar de "recibido_por"
            'recibido_por': 'Estado',  # Se mostrará "Estado" en lugar de "recibido_por"
        }
        widgets = {
            'total': forms.NumberInput(attrs={'step': '0.01'}),
        }
