from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User, Group
from .models import (
    Task, Ot, System, Equipo, Ruta, HistoryHour, FailureReport, Operation, Asset, Location, Document,
    Megger, Estator, Excitatriz, RotorMain, RotorAux, RodamientosEscudos, Solicitud, Suministro,
    Preoperacional, TransaccionSuministro, PreoperacionalDiario
    )

from django.forms import modelformset_factory
from django.utils.timezone import localdate
from django.db.models import Count, Q, Min, OuterRef, Subquery, F, ExpressionWrapper, DateField, Prefetch, Sum


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
        exclude = ['creations_date', 'num_ot', 'ot_aprobada']
        labels = {
            'description': 'Description',
            'system': 'Sistema',
            'state': 'Estado',
            'tipo_mtto': 'Tipo de mantenimiento',
            'info_contratista_pdf': 'Informe externo',
            # 'ot_aprobada': 'OT aprobada',
            'suministros': 'Suministros'
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
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

        group_names = ['serport_members', 'super_members', 'maq_members', 'buzos_members']
        groups = Group.objects.filter(name__in=group_names)
        users = User.objects.filter(groups__in=groups).distinct()
        self.fields['responsible'].queryset = users


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
            }
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'causas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'suggest_repair': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
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


class SuministrosEquipoForm(forms.ModelForm):
    class Meta:
        model = Suministro
        fields = ['item', 'cantidad']
        labels = {
            'item': 'Articulo',
            'cantidad': 'Cantidad'
        }

SuministroFormset = modelformset_factory(
    Suministro,
    fields=('item', 'cantidad',),
    extra=1,
    widgets={
        'item': forms.Select(attrs={'class': 'form-control'}),
        'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
    }
)


class EstatorForm(forms.ModelForm):
    class Meta:
        model = Estator
        exclude = ['megger']
        widgets = {
            'pi_1min_l1_tierra': forms.TextInput(attrs={'class': 'form-control'}),
            'pi_1min_l2_tierra': forms.TextInput(attrs={'class': 'form-control'}),
            'pi_1min_l3_tierra': forms.TextInput(attrs={'class': 'form-control'}),
            'pi_1min_l1_l2': forms.TextInput(attrs={'class': 'form-control'}),
            'pi_1min_l2_l3': forms.TextInput(attrs={'class': 'form-control'}),
            'pi_1min_l3_l1': forms.TextInput(attrs={'class': 'form-control'}),
            'pi_10min_l1_tierra': forms.TextInput(attrs={'class': 'form-control'}),
            'pi_10min_l2_tierra': forms.TextInput(attrs={'class': 'form-control'}),
            'pi_10min_l3_tierra': forms.TextInput(attrs={'class': 'form-control'}),
            'pi_10min_l1_l2': forms.TextInput(attrs={'class': 'form-control'}),
            'pi_10min_l2_l3': forms.TextInput(attrs={'class': 'form-control'}),
            'pi_10min_l3_l1': forms.TextInput(attrs={'class': 'form-control'}),
            'pi_obs_l1_tierra': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'pi_obs_l2_tierra': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'pi_obs_l3_tierra': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'pi_obs_l1_l2': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'pi_obs_l2_l3': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'pi_obs_l3_l1': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),

            'pf_1min_l1_tierra': forms.TextInput(attrs={'class': 'form-control'}),
            'pf_1min_l2_tierra': forms.TextInput(attrs={'class': 'form-control'}),
            'pf_1min_l3_tierra': forms.TextInput(attrs={'class': 'form-control'}),
            'pf_1min_l1_l2': forms.TextInput(attrs={'class': 'form-control'}),
            'pf_1min_l2_l3': forms.TextInput(attrs={'class': 'form-control'}),
            'pf_1min_l3_l1': forms.TextInput(attrs={'class': 'form-control'}),
            'pf_10min_l1_tierra': forms.TextInput(attrs={'class': 'form-control'}),
            'pf_10min_l2_tierra': forms.TextInput(attrs={'class': 'form-control'}),
            'pf_10min_l3_tierra': forms.TextInput(attrs={'class': 'form-control'}),
            'pf_10min_l1_l2': forms.TextInput(attrs={'class': 'form-control'}),
            'pf_10min_l2_l3': forms.TextInput(attrs={'class': 'form-control'}),
            'pf_10min_l3_l1': forms.TextInput(attrs={'class': 'form-control'}),
            'pf_obs_l1_tierra': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'pf_obs_l2_tierra': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'pf_obs_l3_tierra': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'pf_obs_l1_l2': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'pf_obs_l2_l3': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'pf_obs_l3_l1': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ExcitatrizForm(forms.ModelForm):
    class Meta:
        model = Excitatriz
        exclude = ['megger']

        widgets = {
                'pi_1min_l_tierra' : forms.TextInput(attrs={'class': 'form-control'}), 
                'pi_10min_l_tierra' : forms.TextInput(attrs={'class': 'form-control'}),
                'pi_obs_l_tierra' : forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),

                'pf_1min_l_tierra' : forms.TextInput(attrs={'class': 'form-control'}), 
                'pf_10min_l_tierra' : forms.TextInput(attrs={'class': 'form-control'}), 
                'pf_obs_l_tierra' : forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class RotorMainForm(forms.ModelForm):
    class Meta:
        model = RotorMain
        exclude = ['megger']

class RotorAuxForm(forms.ModelForm):
    class Meta:
        model = RotorAux
        exclude = ['megger']

class RodamientosEscudosForm(forms.ModelForm):
    class Meta:
        model = RodamientosEscudos
        exclude = ['megger']

class MeggerForm(forms.ModelForm):
    class Meta:
        model = Megger
        fields = '__all__'


class TransaccionSuministroForm(forms.ModelForm):
    class Meta:
        model = TransaccionSuministro
        fields = ['cantidad_ingresada', 'cantidad_consumida']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cantidad_ingresada'].widget.attrs.update({'class': 'form-control'})
        self.fields['cantidad_consumida'].widget.attrs.update({'class': 'form-control'})


class PreoperacionalForm(forms.ModelForm):

    vehiculo = forms.ModelChoiceField(queryset=System.objects.filter(asset__area='v'), empty_label="Seleccione un Vehículo", widget=forms.Select(attrs={'class': 'form-control'}))
    nuevo_kilometraje = forms.IntegerField(label="Kilometraje Actual", required=True, widget=forms.NumberInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Preoperacional
        fields = ['nombre_no_registrado', 'cedula', 'motivo', 'salida', 'destino', 'tipo_ruta', 'autorizado', 'observaciones', 'vehiculo', 'nuevo_kilometraje']
        labels = {
            'nombre_no_registrado': 'Nombre y apellido del solicitante',
            'cedula': 'Cédula del solicitante',
            'motivo': 'Motivo del desplazamiento',
            'salida': 'Punto de salida',
            'destino': 'Destino',
            'tipo_ruta': 'Tipo de ruta',
            'autorizado': 'Autorizado por',
            'Observaciones': 'HALLAZGOS ENCONTRADOS EN EL VEHÍCULO ANTES DE LA SALIDA (En esta sección se deberá remitir evidencia de inconsistencias encontradas en el vehículo antes de la salida de las instalaciones de SERPORT).',
        }
        widgets = {
                'nombre_no_registrado' : forms.TextInput(attrs={'class': 'form-control'}), 
                'cedula' : forms.TextInput(attrs={'class': 'form-control'}),
                'motivo' : forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
                'salida' : forms.TextInput(attrs={'class': 'form-control'}), 
                'destino' : forms.TextInput(attrs={'class': 'form-control'}), 
                'tipo_ruta': forms.Select(attrs={'class': 'form-control'}),
                'autorizado': forms.Select(attrs={'class': 'form-control'}),
                'observaciones' : forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(PreoperacionalForm, self).__init__(*args, **kwargs)
        if user and user.is_authenticated:
            self.fields['nombre_no_registrado'].widget = forms.HiddenInput()
        else:
            self.fields['nombre_no_registrado'].required = True
        self.fields['vehiculo'].queryset = System.objects.filter(asset__area='v')


class PreoperacionalEspecificoForm(forms.ModelForm):

    choices = [
        (True, 'Sí'),
        (False, 'No'),
    ]

    horas_trabajo = forms.ChoiceField(
        choices=choices,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='¿Las horas de trabajo más las horas de conducción superan 12 horas?',
        required=True,
    )

    medicamentos = forms.ChoiceField(
        choices=choices,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='¿Ha ingerido medicamentos que inducen sueño durante el día u horas previas a la jornada laboral?',
        required=True,
    )

    molestias = forms.ChoiceField(
        choices=choices,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='¿Ha consultado al médico o asistido a urgencias por alguna molestia que le dificulte conducir?',
        required=True,
    )

    enfermo = forms.ChoiceField(
        choices=choices,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='¿Se encuentra enfermo o con alguna condición que le impida conducir?',
        required=True,
    )

    condiciones = forms.ChoiceField(
        choices=choices,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='¿Se siente en condiciones para conducir en la jornada asignada?',
        required=True,
    )

    agua = forms.ChoiceField(
        choices=choices,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='¿Tiene agua para beber?',
        required=True,
    )

    dormido = forms.ChoiceField(
        choices=choices,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='¿Ha dormido al menos 8 horas en las últimas 24 horas?',
        required=True,
    )

    control = forms.ChoiceField(
        choices=choices,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='¿Conoce los puestos de control en la vía? (Planifico e identifico los lugares de descanso)',
        required=True,
    )

    sueño = forms.ChoiceField(
        choices=choices,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='¿En caso de sentir sueño sabe qué hacer?',
        required=True,
    )

    radio_aire = forms.ChoiceField(
        choices=choices,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='¿El vehículo que conduce tiene radio y aire acondicionado?',
        required=True,
    )
        
    nuevo_kilometraje = forms.IntegerField(
        label="Kilometraje Actual",
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Preoperacional
        fields = ['nombre_no_registrado', 'cedula', 'nuevo_kilometraje', 'motivo', 'salida', 'destino', 'tipo_ruta', 'autorizado', 'observaciones', 'horas_trabajo', 'medicamentos', 'molestias', 'enfermo', 'condiciones', 'agua', 'dormido', 'control', 'sueño', 'radio_aire']
        labels = {
            'nombre_no_registrado': 'Nombre y apellido del solicitante',
            'cedula': 'Cédula del solicitante',
            'motivo': 'Motivo del desplazamiento',
            'salida': 'Punto de salida',
            'destino': 'Destino',
            'tipo_ruta': 'Tipo de ruta',
            'autorizado': 'Autorizado por',
            'observaciones': 'HALLAZGOS ENCONTRADOS EN EL VEHÍCULO ANTES DE LA SALIDA (En esta sección se deberá remitir evidencia de inconsistencias encontradas en el vehículo antes de la salida de las instalaciones de SERPORT).',
        }
        widgets = {
            'nombre_no_registrado': forms.TextInput(attrs={'class': 'form-control'}),
            'cedula': forms.TextInput(attrs={'class': 'form-control'}),
            'motivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'salida': forms.TextInput(attrs={'class': 'form-control'}),
            'destino': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_ruta': forms.Select(attrs={'class': 'form-control'}),
            'autorizado': forms.Select(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        equipo_code = kwargs.pop('equipo_code', None)
        user = kwargs.pop('user', None)
        super(PreoperacionalEspecificoForm, self).__init__(*args, **kwargs)
        self.equipo = Equipo.objects.filter(code=equipo_code).first()

        if user and user.is_authenticated:
            self.fields['nombre_no_registrado'].widget = forms.HiddenInput()
        else:
            self.fields['nombre_no_registrado'].required = True

    def clean_nuevo_kilometraje(self):
        nuevo_kilometraje = self.cleaned_data.get('nuevo_kilometraje')
        if self.equipo and nuevo_kilometraje < self.equipo.horometro:
            raise forms.ValidationError("El nuevo kilometraje debe ser igual o mayor al kilometraje actual.")
        return nuevo_kilometraje
    

class PreoperacionalDiarioForm(forms.ModelForm):
    
    choices = [
        (True, 'Sí'),
        (False, 'No'),
    ]

    choices_aseo = [
        (True, 'Limpio'),
        (False, 'Sucio'),
    ]

    choices_completo = [
        (True, 'Completo'),
        (False, 'Incompleto'),
    ]

    choices_aprobado = [
        (True, 'Aprobado'),
        (False, 'No aprobado'),
    ]

    is_llanta_repuesto = forms.ChoiceField(
        choices=choices,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='¿Tiene llanta de repuesto?',
        initial=False,
        required=False,
    )

    aseo_externo = forms.ChoiceField(
        choices=choices_aseo,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='Aseo externo',
        initial=True,
        required=False,
    )

    aseo_interno = forms.ChoiceField(
        choices=choices_aseo,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='Aseo interno',
        initial=True,
        required=False,
    )

    kit_carreteras = forms.ChoiceField(
        choices=choices_completo,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='Kit de carreteras',
        initial=True,
        required=False,
    )
    
    kit_herramientas = forms.ChoiceField(
        choices=choices_completo,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='Kit de herramientas',
        initial=True,
        required=False,
    )

    kit_botiquin = forms.ChoiceField(
        choices=choices_completo,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='Kit de botiquín',
        initial=True,
        required=False,
    )

    chaleco_reflectivo = forms.ChoiceField(
        choices=choices,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='IMPLEMENTOS DE SEGURIDAD VIAL ¿Tiene chalecos reflectivos?',
        initial=True,
        required=False,
    )

    aprobado = forms.ChoiceField(
        choices=choices_aprobado,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='CERTIFICO QUE EL VEHÍCULO INSPECCIONADO ESTÁ ADECUADO PARA SER UTILIZADO DURANTE EL DÍA DE LA INSPECCIÓN REALIZADA:',
        initial=True,
        required=False,
    )


    class Meta:
        model = PreoperacionalDiario
        exclude = ['vehiculo', 'fecha', 'reporter']
        labels = {
            'nombre_no_registrado': 'Nombre y apellido del solicitante',
            'kilometraje': 'Kilometraje Actual',
            'combustible_level': 'Nivel de combustible',
            'aceite_level': 'Nivel de aceite del motor',
            'refrigerante_level': 'Nivel de refrigerante radiador',
            'hidraulic_level': 'Nivel de aceite dirección hidráulica',
            'liq_frenos_level': 'Nivel de liquido de frenos',

            'poleas': 'Estado de poleas',
            'correas': 'Estado de correas',
            'mangueras': 'Estado de mangueras',
            'acoples': 'Estado de acoples',
            'tanques': 'Control liqueo en tanques',
            'radiador': 'Estado del radiador',
            'terminales': 'Estado de terminales',
            'bujes': 'Estado de bujes',
            'rotulas': 'Estado de rotulas',
            'ejes': 'Estado de ejes',
            'cruceta': 'Estado de cruceta',
            'puertas': 'Estado de puertas',
            'chapas': 'Estado de chapas',
            'manijas': 'Estado de manijas',
            'elevavidrios': 'Estado de eleva vidrios',
            'lunas': 'Estado de lunas',
            'espejos': 'Estado de espejos',
            'vidrio_panoramico': 'Estado de vidrio panoramico',
            'asiento': 'Estado de asientos',
            'apoyacabezas': 'Estado de apoya cabezas',
            'cinturon': 'Estado de cinturones de seguridad',
            'aire': 'Estado sistema de aire acondicionado',
            'caja_cambios': 'ESTADO DE CAJA DE CAMBIOS (General)',
            'direccion': 'Estado de dirección',
            'bateria': 'Estado de bateria (Verificar bornes sueltos, sulfatados)',
            'luces_altas': 'Estado de luces altas',
            'luces_medias': 'Estado de luces medias',
            'luces_direccionales': 'Estado de luces direccionales',
            'cocuyos': 'Estado de cocuyos',
            'luz_placa': 'Estado de luz placa',
            'luz_interna': 'Estado de luz interna de cabina',
            'pito': 'Estado del pito',
            'alarma_retroceso': 'Estado alarma de retroceso',
            'arranque': 'Estado del arranque',
            'alternador': 'Estado del alternador',
            'rines': 'Estado de rines',
            'tuercas': 'Estado de tuercas',
            'esparragos': 'Estado de esparragos',
            'freno_servicio': 'Estado del freno de servicio',
            'freno_seguridad': 'Estado del freno de seguridad',
            'is_llanta_repuesto': '¿Tiene llanta de repuesto?',
            'llantas': 'Estado general de llantas - Huella Mínima de 5 mm (cortaduras, abultamientos)',
            'suspencion': 'Estado de suspención',
            
            'capo': 'Estado del capo',
            'persiana': 'Estado de la persiana',
            'bumper_delantero': 'Estado del bumper delantero',
            'panoramico': 'Estado del panorámico',
            
            'guardafango': 'Estado de guardafangos',
            'puerta': 'Estado de puertas',
            'parales': 'Estado de parales',
            'stop': 'Estado de stop (freno)',
            'bumper_trasero': 'Estado de bumper trasero',
            'vidrio_panoramico_trasero': 'Estado del vidrio panorámico trasero',
            'placa_delantera': 'Estado de la placa delantera',
            'placa_trasera': 'Estado de la placa trasera',
            'observaciones': 'HALLAZGOS ENCONTRADOS EN EL VEHÍCULO ANTES DE LA SALIDA (En esta sección se deberá remitir evidencia de inconsistencias encontradas en el vehículo antes de la salida de las instalaciones de SERPORT).',
        }
        widgets = {
            'nombre_no_registrado': forms.TextInput(attrs={'class': 'form-control'}),
            'kilometraje': forms.NumberInput(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'combustible_level': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),

            'aceite_level': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'refrigerante_level': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'hidraulic_level': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'liq_frenos_level': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            
            'poleas': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'correas': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'mangueras': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'acoples': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'tanques': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'radiador': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'terminales': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'bujes': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'rotulas': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'ejes': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'cruceta': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'puertas': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'chapas': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'manijas': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'elevavidrios': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'lunas': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'espejos': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'vidrio_panoramico': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'asiento': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'apoyacabezas': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'cinturon': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'aire': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'caja_cambios': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'direccion': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'bateria': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'luces_altas': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'luces_medias': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'luces_direccionales': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'cocuyos': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'luz_placa': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'luz_interna': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'pito': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'alarma_retroceso': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'arranque': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'alternador': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'rines': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'tuercas': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'esparragos': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'freno_servicio': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'freno_seguridad': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),

            'llantas': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'suspencion': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'capo': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'persiana': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'bumper_delantero': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'panoramico': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'guardafango': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'puerta': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'parales': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'stop': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'bumper_trasero': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'vidrio_panoramico_trasero': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'placa_delantera': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'placa_trasera': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'aseo_externo': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'aseo_interno': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'kit_carreteras': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'kit_herramientas': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'kit_botiquin': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'chaleco_reflectivo': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
            'aprobado': forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),

            
        }

    def __init__(self, *args, **kwargs):
        equipo_code = kwargs.pop('equipo_code', None)
        user = kwargs.pop('user', None)
        super(PreoperacionalDiarioForm, self).__init__(*args, **kwargs)
        self.equipo = Equipo.objects.filter(code=equipo_code).first()
        print(equipo_code)
        if user and user.is_authenticated:
            self.fields['nombre_no_registrado'].widget = forms.HiddenInput()
        else:
            self.fields['nombre_no_registrado'].required = True
            

    def clean_kilometraje(self):
        kilometraje = self.cleaned_data['kilometraje']
        if kilometraje < self.equipo.horometro:
            raise ValidationError("El nuevo kilometraje debe ser igual o mayor al kilometraje actual.")
        return kilometraje



    
