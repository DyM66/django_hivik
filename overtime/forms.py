from django import forms
from .models import *
from django.forms import formset_factory
from django.core.exceptions import ValidationError


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
        fields = ['nombre_completo', 'cedula', 'hora_inicio', 'hora_fin', 'justificacion']
        widgets = {
            'nombre_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control'}),
            'justificacion': forms.Textarea(attrs={'class': 'form-control'}),
        }

class OvertimePersonForm(forms.Form):
    nombre_completo = forms.CharField(max_length=200, label='Nombre completo', widget=forms.TextInput(attrs={'class': 'form-control'}))
    cedula = forms.CharField(max_length=20, label='Cédula', widget=forms.TextInput(attrs={'class': 'form-control'}))
    cargo = forms.ChoiceField(
        choices=[('', '---')] + list(Overtime.CARGO),
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

OvertimePersonFormSet = formset_factory(OvertimePersonForm, extra=1)

class OvertimeCommonForm(forms.Form):
    fecha = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    hora_inicio = forms.TimeField(
        input_formats=['%I:%M %p'],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'timepicker_inicio',
            'placeholder': 'Seleccione la hora de inicio'
        })
    )
    hora_fin = forms.TimeField(
        input_formats=['%I:%M %p'],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'timepicker_fin',
            'placeholder': 'Seleccione la hora de finalización'
        })
    )
    justificacion = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control'}))

    def clean(self):
        cleaned_data = super().clean()
        hora_inicio = cleaned_data.get('hora_inicio')
        hora_fin = cleaned_data.get('hora_fin')

        if hora_inicio and hora_fin:
            if hora_fin <= hora_inicio:
                raise ValidationError('La hora de finalización debe ser posterior a la hora de inicio.')