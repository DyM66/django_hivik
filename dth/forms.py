from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import formset_factory

from dth.models import UserProfile, Overtime, Nomina
from got.models import Asset

class UploadNominaReportForm(forms.Form):
    excel_file = forms.FileField(
        label="Cargar Archivo Excel",
        help_text="Sube un archivo .xlsx con las columnas requeridas."
    )


class NominaForm(forms.ModelForm):
    """
    Formulario para crear/editar registros de Nomina.
    """
    class Meta:
        model = Nomina
        fields = ['doc_number', 'name', 'surname', 'position', 'salary']
        # Si quieres personalizar etiquetas o widgets, puedes hacerlo aquí:
        labels = {
            'doc_number': 'Cédula del Empleado',
            'name': 'Nombre',
            'surname': 'Apellidos',
            'position': 'Cargo',
            'salary': 'Salario',
            # 'dpto': 'Departamento',
            # 'category': 'Categoría',
        }

class UserChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):
        try:
            cargo = obj.profile.cargo if obj.profile.cargo else "Sin cargo"
        except UserProfile.DoesNotExist:
            cargo = "Sin cargo"
        
        if obj.groups.filter(name="maq_members").exists():
            try:
                asset = Asset.objects.get(Q(supervisor=obj) | Q(capitan=obj))
                asset_name = f" ({asset})"
            except Asset.DoesNotExist:
                asset_name = ""
            return f"{obj.get_full_name()} - {cargo}{asset_name}"
        else:
            return f"{obj.get_full_name()} - {cargo}"


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(label='Nombre', max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu nombre'}))
    last_name = forms.CharField(label='Apellido', max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu apellido'}))
    email = forms.EmailField(label='Correo electrónico', required=False, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': '@serport.co'}))

    class Meta:
        model = UserProfile
        fields = ['cargo', 'firma']
        labels = {
            'cargo': 'Cargo',
            'firma': 'Firma'
        }
        widgets = {
            'cargo': forms.TextInput(attrs={'class': 'form-control'}),
            'firma': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(UserProfileForm, self).__init__(*args, **kwargs)


class OvertimeEditForm(forms.ModelForm):
    hora_inicio = forms.TimeField(input_formats=['%I:%M %p', '%H:%M'], widget=forms.TextInput(attrs={'class': 'form-control timepicker'}),)
    hora_fin = forms.TimeField(input_formats=['%I:%M %p', '%H:%M'], widget=forms.TextInput(attrs={'class': 'form-control timepicker'}),)

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
    cargo = forms.ChoiceField(choices=[('', '---')] + list(Overtime.CARGO), required=True, widget=forms.Select(attrs={'class': 'form-control'}))

OvertimePersonFormSet = formset_factory(OvertimePersonForm, extra=1)

class OvertimeCommonForm(forms.Form):
    fecha = forms.DateField(widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    hora_inicio = forms.TimeField(input_formats=['%I:%M %p'],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'timepicker_inicio',
            'placeholder': 'Seleccione la hora de inicio'
        })
    )
    hora_fin = forms.TimeField(input_formats=['%I:%M %p'],
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