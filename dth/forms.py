from django import forms
from django.db.models import Q
from datetime import date

from dth.models import UserProfile, Overtime, OvertimeProject, Nomina
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
        fields = [
            'id_number', 'name', 'surname', 'position', 'salary', 'admission', 
            'expiration', 'risk_class', 'is_driver', 'gender', 'photo'
        ]
        # Si quieres personalizar etiquetas o widgets, puedes hacerlo aquí:
        labels = {
            'id_number': 'Cédula del Empleado',
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
        fields = ['nombre_completo', 'cedula', 'hora_inicio', 'hora_fin']
        widgets = {
            'nombre_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control'}),
        }


class OvertimeProjectForm(forms.ModelForm):
    start = forms.TimeField(label="Hora de Inicio")
    end = forms.TimeField(label="Hora de Fin")
    cedulas = forms.CharField(widget=forms.HiddenInput(), required=False)
    personas_externas = forms.CharField(widget=forms.HiddenInput(), required=False)

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
        
        # Ajustar la etiqueta de 'report_date' si deseas (por defecto dice 'Report date')
        self.fields['report_date'].label = "Fecha"

    def clean_report_date(self):
        data = self.cleaned_data['report_date']
        if data > date.today():
            raise forms.ValidationError("No puedes reportar horas en una fecha futura.")
        return data

    #     try:
    #         cedulas = json.loads(cedulas)
    #     except json.JSONDecodeError:
    #         raise forms.ValidationError("Error al procesar los datos del personal.")

    #     trabajadores = Nomina.objects.filter(id_number__in=cedulas)

    #     overtime_periods = calcular_horas_extras(report_date, start, end)
    #     if not overtime_periods:
    #         raise forms.ValidationError("Las horas reportadas no califican como horas extras.")

    #     conflictos_totales = 0
    #     for trabajador in trabajadores:
    #         for ot_start, ot_end in overtime_periods:
    #             conflictos = Overtime.objects.filter(worker=trabajador, project__report_date=report_date).filter(Q(start__lt=ot_end, end__gt=ot_start)).exists()
    #             if conflictos:
    #                 conflictos_totales += 1

    #     if conflictos_totales == len(trabajadores) * len(overtime_periods):
    #         raise forms.ValidationError("Todos los trabajadores tienen conflictos en las horas reportadas.")

    #     cleaned_data['trabajadores'] = trabajadores
    #     cleaned_data['overtime_periods'] = overtime_periods

    #     return cleaned_data

#     hora_fin = forms.TimeField(input_formats=['%I:%M %p'],
#         widget=forms.TextInput(attrs={
#             'class': 'form-control',
#             'id': 'timepicker_fin',
#             'placeholder': 'Seleccione la hora de finalización'
#         })
#     )
#     # justificacion = forms.CharField(widget= )
