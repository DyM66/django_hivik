from django import forms
from django.db.models import Q

from dth.models import UserProfile, Overtime, OvertimeProject, Nomina
from dth.models.positions import Position, Document
from got.models import Asset


class UploadNominaReportForm(forms.Form):
    excel_file = forms.FileField(
        label="Cargar Archivo Excel",
        help_text="Sube un archivo .xlsx con las columnas requeridas."
    )


class PositionForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = ['name', 'description', 'category']
        labels = {
            'name': 'Nombre del Cargo',
            'description': 'Descripción breve',
            'category': 'Categoria',     
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
        }


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['name', 'description']
        labels = {
            'name': 'Nombre del documento',
            'description': 'Descripción breve',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Titulo del documento'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }


class NominaForm(forms.ModelForm):
    class Meta:
        model = Nomina
        fields = [
            'id_number', 'name', 'surname', 'position_id', 'is_driver',
            'gender', 'photo', 'email', 'employment_status'
        ]
        labels = {
            'id_number': 'No Cédula',
            'name': 'Nombres',
            'surname': 'Apellidos',
            'position_id': 'Cargo',
            'admission': 'Fecha de Ingreso',
            'expiration': 'Fecha de Expiración',
            'salary': 'Salario',
            'risk_class': 'Clase de Riesgo',
            'is_driver': '¿Es conductor?',
            'gender': 'Género',
            'photo': 'Foto',
        }
        widgets = {
            'id_number': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'surname': forms.TextInput(attrs={'class': 'form-control'}),
            'position_id': forms.Select(attrs={'class': 'form-select'}),
            'salary': forms.NumberInput(attrs={'class': 'form-control'}),
            'admission': forms.DateInput(format='%Y-%m-%d', attrs={
                'type': 'date', 'class': 'form-control'
            }),
            'expiration': forms.DateInput(format='%Y-%m-%d', attrs={
                'type': 'date', 'class': 'form-control'
            }),
            'risk_class': forms.Select(attrs={'class': 'form-select'}),
            'is_driver': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
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

