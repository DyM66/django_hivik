# con/forms.py
from django import forms
from .models import Financiacion, AssetCost


class FinanciacionForm(forms.ModelForm):
    class Meta:
        model = Financiacion
        # Excluimos 'asset_cost' para que no se muestre
        fields = [
            'monto',
            'plazo',
            'fecha_desembolso',
            'tasa_interes',
            'no_deuda',
            'periodicidad_pago',
        ]
        widgets = {
            'monto': forms.NumberInput(attrs={'class': 'form-control'}),
            'plazo': forms.NumberInput(attrs={'class': 'form-control'}),
            'fecha_desembolso': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tasa_interes': forms.NumberInput(attrs={'class': 'form-control'}),
            'no_deuda': forms.TextInput(attrs={'class': 'form-control'}),
            'periodicidad_pago': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'asset_cost' in self.fields and self.initial.get('asset_cost'):
            self.fields['asset_cost'].widget = forms.HiddenInput()


class AssetCostUpdateForm(forms.ModelForm):
    class Meta:
        model = AssetCost
        fields = ['initial_cost']

class GastosUploadForm(forms.Form):
    excel_file = forms.FileField(label="Archivo Excel (.xlsx)")
