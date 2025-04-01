from django import forms
from dth.models.overtime import Overtime, OvertimeProject
from got.models import Asset
from datetime import date


class OvertimeEditForm(forms.ModelForm):
    hora_inicio = forms.TimeField(
        input_formats=['%I:%M %p', '%H:%M'],
        widget=forms.TextInput(attrs={'class': 'form-control timepicker'}),
    )
    hora_fin = forms.TimeField(
        input_formats=['%I:%M %p', '%H:%M'],
        widget=forms.TextInput(attrs={'class': 'form-control timepicker'}),
    )

    class Meta:
        model = Overtime
        fields = ['nombre_completo', 'cedula', 'hora_inicio', 'hora_fin']
        widgets = {
            'nombre_completo': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
            'cedula': forms.TextInput(attrs={'class': 'form-control'}),
        }


class OvertimeProjectForm(forms.ModelForm):
    start = forms.TimeField(label="Hora de Inicio")
    end = forms.TimeField(label="Hora de Fin")
    cedulas = forms.CharField(widget=forms.HiddenInput(), required=False)
    personas_externas = forms.CharField(
        widget=forms.HiddenInput(), required=False
        )

    class Meta:
        model = OvertimeProject
        fields = ['report_date', 'description', 'asset']

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Cambiar la etiqueta de 'description'
        self.fields['description'].label = "Justificación"

        # Si el usuario es maq_members, remover asset
        if user and user.groups.filter(name='maq_members').exists():
            self.fields.pop('asset', None)
        else:
            # Solo mostrar assets con show=True
            self.fields['asset'].queryset = Asset.objects.filter(show=True)
            self.fields['asset'].label = "Centro de costos"

        self.fields['report_date'].label = "Fecha"

    def clean_report_date(self):
        data = self.cleaned_data['report_date']
        if data > date.today():
            raise forms.ValidationError(
                "No puedes reportar horas en una fecha futura."
                )
        return data
