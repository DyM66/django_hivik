# inv/forms/retirement_forms.py
from django import forms
from django.forms.widgets import ClearableFileInput
from inv.models.equipment_retirement import RetiredSupply

class RetiredSupplyForm(forms.ModelForm):
    """Formulario principal para los datos de la baja de suministro."""
    class Meta:
        model = RetiredSupply
        fields = ['supervisor', 'amount', 'reason', 
                  'remark', 'provision']
        widgets = {
            'remark': forms.Textarea(attrs={'rows':3}),
            'provision': forms.Textarea(attrs={'rows':3}),
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