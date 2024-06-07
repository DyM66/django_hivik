from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User, Group
from .models import (
    Task, Ot, System, Equipo, Ruta, HistoryHour, FailureReport, Operation, Asset, Location, Document, Megger, Solicitud, Suministro
    )


# ---------------- Widgets ------------------- #
class UserChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):
        return f'{obj.first_name} {obj.last_name}'


class XYZ_DateInput(forms.DateInput):

    input_type = 'date'

    def __init__(self, **kwargs):
        kwargs['format'] = '%Y-%m-%d'
        super().__init__(**kwargs)


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result
    

class UploadImages(forms.Form):
    file_field = MultipleFileField(label='Evidencias', required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file_field'].widget.attrs.update({'multiple': True})


# ---------------- Systems ------------------- #
class SysForm(forms.ModelForm):

    class Meta:
        model = System
        exclude = ['asset',]
        labels = {
            'name': 'Sistema',
            'group': 'Grupo',
            'location': 'Ubicación',
            'state': 'Estado'
        }


# ---------------- Equipos ------------------- #
class EquipoForm(forms.ModelForm):

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if Equipo.objects.filter(code=code).exists():
            raise ValidationError(
                '''Este código ya está en uso. Por favor,
                ingresa un código diferente.'''
                )
        return code

    class Meta:
        model = Equipo
        exclude = ['system', 'horometro', 'prom_hours']
        labels = {
            'name': 'Nombre',
            'date_inv': 'Fecha de ingreso al inventario',
            'code': 'Codigo interno',
            'model': 'Modelo',
            'serial': '# Serial',
            'marca': 'Marca',
            'fabricante': 'Fabricante',
            'feature': 'Caracteristicas',
            'imagen': 'Imagen',
            'manual_pdf': 'Manual',
            'tipo': 'tipo de equipo:',
            'initial_hours': 'Horas iniciales (Si aplica)',
            'lubricante': 'Lubricante (Si aplica)',
            'volumen': 'Capacidad lubricante - Galones (Si aplica)',
            'subsystem': 'Categoria (Si aplica)'
            }
        widgets = {
            'date_inv': XYZ_DateInput(format=['%Y-%m-%d'],),
            'feature': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'imagen': forms.FileInput(attrs={'class': 'form-control'}),
            'manual_pdf': forms.FileInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            }


class EquipoFormUpdate(forms.ModelForm):

    class Meta:
        model = Equipo
        exclude = ['system', 'horometro', 'prom_hours', 'code']
        labels = {
            'name': 'Nombre',
            'date_inv': 'Fecha de ingreso al inventario',
            'model': 'Modelo',
            'serial': '# Serial',
            'marca': 'Marca',
            'fabricante': 'Fabricante',
            'feature': 'Caracteristicas',
            'imagen': 'Imagen',
            'manual_pdf': 'Manual',
            'tipo': 'tipo de equipo:',
            'initial_hours': 'Horas iniciales (si aplica)'
            }
        widgets = {
            'date_inv': XYZ_DateInput(format=['%Y-%m-%d'],),
            'feature': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'imagen': forms.FileInput(attrs={'class': 'form-control'}),
            'manual_pdf': forms.FileInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            }


# ----------------- OTs -------------------- #
class OtForm(forms.ModelForm):

    super = UserChoiceField(
        queryset=User.objects.none(),
        label='Supervisor',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = Ot
        exclude = ['creations_date', 'num_ot']
        labels = {
            'description': 'Description',
            'system': 'Sistema',
            'state': 'Estado',
            'tipo_mtto': 'Tipo de mantenimiento',
            'info_contratista_pdf': 'Informe externo',
            'ot_aprobada': 'OT aprobada',
            'suministros': 'Suministros'
        }
        widgets = {
            'info_contratista_pdf': forms.FileInput(attrs={'class': 'form-control'}),
            'tipo_mtto': forms.Select(attrs={'class': 'form-control'}),
            'system': forms.Select(attrs={'class': 'form-control'}),
            'state': forms.Select(attrs={'class': 'form-control'}),
            'suministros': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        asset = kwargs.pop('asset')
        super().__init__(*args, **kwargs)
        self.fields['system'].queryset = System.objects.filter(asset=asset)
        super_members_group = Group.objects.get(name='super_members')
        self.fields['super'].queryset = super_members_group.user_set.all()


class OtFormNoSup(forms.ModelForm):

    class Meta:
        model = Ot
        exclude = ['creations_date', 'num_ot', 'super']
        labels = {
            'description': 'Description',
            'system': 'Sistema',
            'state': 'Estado',
            'tipo_mtto': 'Tipo de mantenimiento',
            'info_contratista_pdf': 'Informe externo',
            'suministros': 'Suministros'
        }
        widgets = {
            'info_contratista_pdf': forms.FileInput(attrs={'class': 'form-control'}),
            'tipo_mtto': forms.Select(attrs={'class': 'form-control'}),
            'system': forms.Select(attrs={'class': 'form-control'}),
            'state': forms.Select(attrs={'class': 'form-control'}),
            'suministros': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        asset = kwargs.pop('asset')
        super().__init__(*args, **kwargs)
        self.fields['system'].queryset = System.objects.filter(asset=asset)


class FinishOtForm(forms.Form):
    finish = forms.BooleanField(
        widget=forms.HiddenInput(),
        required=False,
        initial=True,
    )


# ---------------- Actividades ------------------- #
class RescheduleTaskForm(forms.ModelForm):

    news = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False,
        label='Novedades'
        )

    class Meta:
        model = Task
        fields = ['start_date', 'news', 'men_time']
        labels = {
            'start_date': 'Fecha de reprogramacion',
            'men_time': 'Tiempo de ejecución (Dias)'
            }
        widgets = {
            'start_date': XYZ_DateInput(format=['%Y-%m-%d']),
            }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        men_time = cleaned_data.get('men_time')

        if not start_date and not men_time:
            raise forms.ValidationError('Debe proporcionar una nueva fecha de inicio y/o tiempo de ejecución.')
        
        return cleaned_data


class FinishTask(forms.ModelForm):

    finished = forms.ChoiceField(
        choices=[(True, 'Sí'), (False, 'No')],
        widget=forms.RadioSelect,
        label='Finalizado',
        initial=False,
        required=False
    )

    class Meta:
        model = Task
        fields = ['news', 'finished']
        labels = {
                'news': 'Novedades',
                }
        widgets = {
            'news': forms.Textarea,
        }

    def __init__(self, *args, **kwargs):
        super(FinishTask, self).__init__(*args, **kwargs)
        self.fields['finished'].widget.attrs.update({'class': 'btn-group-toggle', 'data-toggle': 'buttons'})


class ActForm(forms.ModelForm):

    delete_images = forms.BooleanField(required=False, label='Eliminar imágenes')
    responsible = UserChoiceField(queryset=User.objects.all(), label='Responsable')

    finished = forms.ChoiceField(
        choices=[(True, 'Sí'), (False, 'No')],
        widget=forms.RadioSelect,
        label='Finalizado',
        initial=False,
        required=False
    )

    class Meta:
        model = Task
        fields = ['responsible', 'description', 'news', 'start_date', 'men_time', 'finished']
        labels = {
            'description': 'Descripción',
            'news': 'Novedades',
            'start_date': 'Fecha de inicio',
            'men_time': 'Tiempo de ejecución (Dias)',
            }
        widgets = {
            'responsible': forms.Select,
            'start_date': XYZ_DateInput(format=['%Y-%m-%d'],),
            'description': forms.Textarea,
            }

    def __init__(self, *args, **kwargs):
        super(ActForm, self).__init__(*args, **kwargs)
        self.fields['start_date'].required = True
        self.fields['finished'].widget.attrs.update({'class': 'btn-group-toggle', 'data-toggle': 'buttons'})


class ActFormNoSup(forms.ModelForm):

    class Meta:
        model = Task
        fields = ['description', 'news', 'start_date', 'men_time', 'finished']
        labels = {
            'description': 'Descripción',
            'news': 'Novedades',
            'start_date': 'Fecha de inicio',
            'men_time': 'Tiempo de ejecución (Dias)',
        }
        widgets = {
            'start_date': XYZ_DateInput(format=['%Y-%m-%d'],),
            'description': forms.Textarea,
        }

    def __init__(self, *args, **kwargs):
        super(ActFormNoSup, self).__init__(*args, **kwargs)
        self.fields['start_date'].required = True
        self.fields['finished'].widget.attrs.update({'class': 'btn-group-toggle', 'data-toggle': 'buttons'})


class RutActForm(forms.ModelForm):
    responsible = UserChoiceField(queryset=User.objects.all(), label='Responsable', required=False,)

    class Meta:
        model = Task
        fields = ['responsible', 'description', 'procedimiento', 'hse', 'priority']
        labels = {
            'responsible': 'Responsable(Opcional)',
            'description': 'Descripción',
            'procedimiento': 'Procedimiento',
            'hse': 'Precauciones de seguridad',
            }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'procedimiento': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'hse': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'responsible': forms.Select(attrs={'class': 'form-control'}),
            }


# ---------------- Rutinas ------------------- #
class RutaForm(forms.ModelForm):

    def clean(self):
        cleaned_data = super().clean()
        control = cleaned_data.get('control')
        equipo = cleaned_data.get('equipo')

        if control == 'h' and not equipo:
            self.add_error(
                'equipo',
                'Seleccionar un equipo es obligatorio para el control en horas'
                )
        return cleaned_data

    def clean_frecuency(self):
        frecuency = self.cleaned_data['frecuency']

        if frecuency < 0:
            raise forms.ValidationError(
                'El valor de la frecuencia no puede ser 0.'
                )
        return frecuency

    class Meta:
        model = Ruta
        exclude = ['system', 'code', 'astillero']
        labels = {
            'name': 'Codigo interno',
            'frecuency': 'Frecuencia',
            'intervention_date': 'Fecha ultima intervención',
            'dependencia': 'Dependencia',
            'suministros': 'Suministros'
            }
        widgets = {
            'intervention_date': XYZ_DateInput(format=['%Y-%m-%d'],),
            'suministros': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            }

    def __init__(self, *args, **kwargs):
        system = kwargs.pop('system')
        super(RutaForm, self).__init__(*args, **kwargs)
        self.fields['equipo'].queryset = Equipo.objects.filter(system=system)
        self.fields['ot'].queryset = Ot.objects.filter(system__asset=system.asset)
        self.fields['dependencia'].queryset = Ruta.objects.filter(system=system).exclude(code=self.instance.code if self.instance else None)


# ---------------- Hours ------------------- #
class ReportHours(forms.ModelForm):
    def clean_hour(self):
        hour = self.cleaned_data['hour']
        if hour < 0 or hour > 24:
            raise forms.ValidationError(
                'El valor de horas debe estar entre 0 y 24.'
                )
        return hour

    class Meta:
        model = HistoryHour
        fields = ['hour', 'report_date']
        labels = {
            'hour': 'Horas',
            'report_date': 'Fecha'
        }
        widgets = {'report_date': XYZ_DateInput(format=['%Y-%m-%d'],), }


class ReportHoursAsset(forms.ModelForm):

    class Meta:
        model = HistoryHour
        fields = ['hour', 'report_date', 'component']
        labels = {
            'hour': 'Horas',
            'report_date': 'Fecha',
            'component': 'Componente',
        }
        widgets = {
            'report_date': XYZ_DateInput(format=['%Y-%m-%d'],),
            'component': forms.Select(attrs={'class': 'form-control'}),
            }


    def __init__(self, *args, **kwargs):
        asset = kwargs.pop('asset', None)
        super(ReportHoursAsset, self).__init__(*args, **kwargs)
        if asset:
            self.fields['component'].queryset = Equipo.objects.filter(system__asset=asset, tipo='r')

    def clean(self):
        cleaned_data = super().clean()
        component = cleaned_data.get('component')
        report_date = cleaned_data.get('report_date')
        hour = cleaned_data.get('hour')
        
        if hour < 0 or hour > 24:
            raise ValidationError('El valor de horas debe estar entre 0 y 24.')

        existing = HistoryHour.objects.filter(component=component, report_date=report_date).first()
        if existing:
            self.instance = existing
            self.cleaned_data['hour'] = hour

        return cleaned_data

    def save(self, commit=True):
        return super(ReportHoursAsset, self).save(commit=commit)


# ---------------- Failure report ------------------- #
class failureForm(forms.ModelForm):

    critico_choices = [
        (True, 'Sí'),
        (False, 'No'),
    ]

    critico = forms.ChoiceField(
        choices=critico_choices,
        widget=forms.RadioSelect(attrs={'class': 'radioOptions'}),
        label='¿El equipo/sistema que presenta la falla es crítico?',
        initial=False,
        required=False,
    )

    impact = forms.MultipleChoiceField(
        choices=FailureReport.IMPACT,
        widget=forms.CheckboxSelectMultiple(
            attrs={'class': 'custom-checkbox'}
        ),
        required=False,
        label='Impacto',
    )

    class Meta:
        model = FailureReport
        exclude = ['reporter', 'related_ot', 'closed', 'evidence']
        labels = {
            'equipo': 'Equipo que presenta la falla',
            'critico': '¿Equipo/sistema que presenta la falla es critico?',
            'description': 'Descripción detallada de falla presentada',
            'impact': 'Seleccione las areas afectadas por la falla',
            'causas': 'Describa las causas probable de la falla',
            'suggest_repair': 'Reparación sugerida',
            # 'evidence': 'Evidencia',
            }
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'causas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'suggest_repair': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            # 'evidence': forms.FileInput(attrs={'class': 'form-control'}),
        }


# ---------------- Operaciones ------------------- #
class OperationForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(OperationForm, self).__init__(*args, **kwargs)
        self.fields['asset'].queryset = Asset.objects.filter(area='a')

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start')
        end = cleaned_data.get('end')
        asset = cleaned_data.get('asset')

        if start and end and start > end:
            raise ValidationError({
                'start': 'La fecha de inicio no puede ser posterior a la fecha de fin.',
                'end': 'La fecha de fin no puede ser anterior a la fecha de inicio.'
            })

        if start and end and asset:
            # Comprobar si hay solapamientos con otras operaciones
            overlapping_operations = Operation.objects.filter(
                asset=asset,
                end__gte=start,
                start__lte=end
            )
            if overlapping_operations.exists():
                raise ValidationError('Existe un conflicto entre las fechas seleccionadas.')

        return cleaned_data

    class Meta:
        model = Operation
        fields = ['proyecto', 'asset', 'start', 'end', 'requirements']
        widgets = {
            'start': XYZ_DateInput(format=['%Y-%m-%d'],),
            'end': XYZ_DateInput(format=['%Y-%m-%d'],),
            'requirements': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'asset': 'Equipo',
            'proyecto': 'Nombre del Proyecto',
            'start': 'Fecha de Inicio',
            'end': 'Fecha de Fin',
            'requirements': 'Requerimientos',
        }


class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ['name', 'direccion', 'contact', 'num_contact', 'latitude', 'longitude']
        widgets = {
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput()
        }


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['description', 'file']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'})
        }
        labels = {
            'description': 'Nombre del documento',
            'file': 'Documento'
        }


class SolicitudForm(forms.ModelForm):
    class Meta:
        model = Solicitud
        fields = ['suministros']
        labels = {
            'suministros': 'Suministros'
        }
        widgets = {
            'suministros': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }

class ScForm(forms.ModelForm):
    class Meta:
        model = Solicitud
        fields = ['num_sc']
        labels = {
            'num_sc': 'Numero de solicitud'
        }
        widgets = {
            'num_sc': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class SolicitudAssetForm(forms.ModelForm):
    class Meta:
        model = Solicitud
        fields = ['suministros', 'seccion']
        labels = {
            'suministros': 'Solicitud',
            'seccion': 'Sección'
        }
        widgets = {
            'suminsitros': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

from django.forms import inlineformset_factory
from django.forms import modelformset_factory

# Considerando que ya tienes importado SolicitudForm y tus modelos
# SuministroFormset = inlineformset_factory(
#     Solicitud, Suministro, fields=('item', 'cantidad'), extra=1, can_delete=True
# )

SuministroFormset = modelformset_factory(
    Suministro,
    fields=('item', 'cantidad',),
    extra=1,
    widgets={
        'item': forms.Select(attrs={'class': 'form-control'}),
        'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
    }
)


# class MeggerForm(forms.ModelForm):
#     class Meta:
#         model = Megger
#         fields = '__all__'
#         widgets = {
#             'fecha': XYZ_DateInput(format=['%Y-%m-%d'],),
#             'estator_pi_1min_l1_tierra': forms.NumberInput(attrs={'class': 'form-control'}),
#             # Añade widgets para los demás campos
#         }
#         labels = {
#             'fecha': 'Fecha',
#             'equipo': 'Nombre de equipo',
#             'estator_pi_1min_l1_tierra': 'Prueba inicial',
#         }
