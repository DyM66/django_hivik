# inv/forms.py
from django import forms
from .models import *
from django.forms.widgets import ClearableFileInput
from got.models import System

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

class MultipleFileInput(ClearableFileInput):
    allow_multiple_selected = True
    def __init__(self, attrs=None, *args, **kwargs):
        super().__init__(attrs, *args, **kwargs)
        if self.allow_multiple_selected:
            self.attrs['multiple'] = True

    def value_from_datadict(self, data, files, name):
        if hasattr(files, 'getlist'):
            return files.getlist(name)
        return files.get(name)

    def use_required_attribute(self, initial):
        return False

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(d, initial) for d in data]
        elif data:
            return [single_file_clean(data, initial)]
        return []

class UploadEvidenciasYFirmasForm(forms.Form):
    """
    - file_field => múltiples imágenes de evidencia
    - firma_responsable_file => UNA sola imagen (opcional)
    - firma_autorizado_file => UNA sola imagen (opcional)
    """
    file_field = MultipleFileField(label='Evidencias', required=False)

    firma_responsable_file = forms.ImageField(required=False, label="Firma Responsable (imagen)")

    firma_autorizado_file = forms.ImageField(required=False, label="Firma Autorizado (imagen)")



class TransferenciaForm(forms.ModelForm):
    receptor = forms.CharField(label="Receptor", max_length=150, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre y apellido del receptor'}))
    destino = forms.ModelChoiceField(queryset=System.objects.filter(asset__show=True).select_related('asset').order_by('asset__name', 'name'), label="Sistema Destino", required=True, widget=forms.Select(attrs={'class': 'form-control'}))
    observaciones = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Ingrese observaciones y detalles de la transferencia...'}), label="Justificación", required=False)

    class Meta:
         model = Transferencia
         fields = ['destino', 'receptor', 'observaciones']

    def __init__(self, *args, **kwargs):
         super().__init__(*args, **kwargs)
         self.fields['destino'].label_from_instance = lambda obj: f"{obj.asset.name} - {obj.name}"
