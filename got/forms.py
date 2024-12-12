from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User, Group
from .models import *
from .utils import *
from datetime import datetime

from django.forms import modelformset_factory
from django.utils.timezone import localdate
from django.db.models import Count, Q, Min, OuterRef, Subquery, F, ExpressionWrapper, DateField, Prefetch, Sum
from django.forms.widgets import ClearableFileInput

from django.core.files.base import ContentFile
import base64
import uuid
import re
from django.forms import formset_factory

# ---------------- Widgets ------------------- #
class UserChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):
        try:
            cargo = obj.profile.cargo if obj.profile.cargo else "Sin cargo"
        except UserProfile.DoesNotExist:
            cargo = "Sin cargo"
        
        if obj.groups.filter(name="maq_members").exists():
            try:
                asset = Asset.objects.get(supervisor=obj)
                asset_name = f" ({asset})"
            except Asset.DoesNotExist:
                asset_name = ""
            return f"{obj.get_full_name()} - {cargo}{asset_name}"
        else:
            return f"{obj.get_full_name()} - {cargo}"


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
    

class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(label='Nombre', max_length=30, required=False)
    last_name = forms.CharField(label='Apellido', max_length=30, required=False)
    email = forms.EmailField(label='Correo electrónico', required=False)

    class Meta:
        model = UserProfile
        fields = ['cargo', 'station', 'firma']
        labels = {
            'cargo': 'Cargo',
            'station': 'Estación',
            'firma': 'Firma',
        }
        widgets = {
            'firma': forms.FileInput(),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(UserProfileForm, self).__init__(*args, **kwargs)
        if user and not user.groups.filter(name='buzos_members').exists():
            self.fields.pop('station')
    
    
class RutinaFilterForm(forms.Form):
    current_year = datetime.now().year
    max_year = current_year + 5

    MONTH_CHOICES = [
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
    ]

    YEAR_CHOICES = [(i, str(i)) for i in range(current_year, max_year + 1)]

    month = forms.ChoiceField(
        choices=MONTH_CHOICES,
        initial=datetime.now().month,
        label="Mes",
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    year = forms.ChoiceField(
        choices=YEAR_CHOICES,
        initial=datetime.now().year,
        label="Año",
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    execute = forms.BooleanField(
        required=False,
        initial=False,
        label="Mostrar rutinas en ejecución",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    def __init__(self, *args, **kwargs):
        asset = kwargs.pop('asset', None)
        super().__init__(*args, **kwargs)

        if asset:
            systems = asset.system_set.all().distinct()
            other_asset_systems = System.objects.filter(location=asset.name).exclude(asset=asset).distinct()

            full_systems = systems.union(other_asset_systems).order_by('group')
            locations = full_systems.values_list('location', flat=True)
            
            unique_locations = list(set(locations))  # Eliminar duplicados
            location_choices = [(location, location) for location in unique_locations]
            self.fields['locations'] = forms.MultipleChoiceField(
                choices=location_choices,
                widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
                initial=[location for location in unique_locations],
                required=False,
                label="Ubicaciones"
            )


class UploadImages(forms.Form):
    file_field = MultipleFileField(label='Evidencias', required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file_field'].widget.attrs.update({'multiple': True})


class Rq_Info(forms.Form):
    class Meta:
        model = Solicitud
        fields = ['proveedor', 'inversion']


class SysForm(forms.ModelForm):

    class Meta:
        model = System
        exclude = ['asset', 'modified_by']
        labels = {
            'name': 'Sistema',
            'group': 'Grupo',
            'location': 'Ubicación',
            'state': 'Estado'
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'group': forms.NumberInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.Select(attrs={'class': 'form-control'}),
        }


class EquipoForm(forms.ModelForm):

    critico = forms.ChoiceField(
        choices=[(True, 'Sí'), (False, 'No')],
        widget=forms.RadioSelect,
        label='Equipo crítico',
        initial=False,
        required=False
    )

    class Meta:
        model = Equipo
        exclude = ['system', 'horometro', 'prom_hours', 'code', 'imagen', 'modified_by', 'related']
        labels = {
            'name': 'Nombre',
            'model': 'Modelo',
            'serial': '# Serial',
            'marca': 'Marca',
            'fabricante': 'Fabricante',
            'feature': 'Caracteristicas',
            'manual_pdf': 'Manual',
            'tipo': 'tipo de equipo:',
            'initial_hours': 'Horas iniciales (Motores)',
            'tipo_almacenamiento': 'Tipo de almacenamiento (Tanques)',
            'volumen': 'Capacidad de almacenamiento - Galones (Tanques)',
            'subsystem': 'Categoria (Si aplica)',
            'potencia': 'Potencia (kw)',
            'recomendaciones': 'Recomendaciones',
            }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'serial': forms.TextInput(attrs={'class': 'form-control'}),
            'marca': forms.TextInput(attrs={'class': 'form-control'}),
            'fabricante': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_almacenamiento': forms.TextInput(attrs={'class': 'form-control'}),
            'subsystem': forms.TextInput(attrs={'class': 'form-control'}),
            'initial_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'volumen': forms.NumberInput(attrs={'class': 'form-control'}),
            'potencia': forms.NumberInput(attrs={'class': 'form-control'}),
            'feature': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'manual_pdf': forms.FileInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'ubicacion': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'recomendaciones': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            }

    def __init__(self, *args, **kwargs):
        super(EquipoForm, self).__init__(*args, **kwargs)
        self.fields['critico'].widget.attrs.update({'class': 'btn-group-toggle', 'data-toggle': 'buttons'})



# ----------------- OTs -------------------- #
class OtForm(forms.ModelForm):

    supervisor = UserChoiceField(
        queryset=User.objects.none(),
        label='Supervisor',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = Ot
        fields = ['description', 'system', 'supervisor', 'state', 'tipo_mtto']
        labels = {
            'description': 'Descripción',
            'system': 'Sistema',
            'state': 'Estado',
            'tipo_mtto': 'Tipo de mantenimiento',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'info_contratista_pdf': forms.FileInput(attrs={'class': 'form-control'}),
            'tipo_mtto': forms.Select(attrs={'class': 'form-control'}),
            'system': forms.Select(attrs={'class': 'form-control'}),
            'state': forms.Select(attrs={'class': 'form-control'}),
            # 'sign_supervisor': forms.FileInput(attrs={'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        asset = kwargs.pop('asset')
        super().__init__(*args, **kwargs)
        self.fields['system'].queryset = System.objects.filter(asset=asset)

        super_members_group = Group.objects.get(name='super_members')
        super_members = super_members_group.user_set.all()
        supervisor_choices = [(member.get_full_name(), member.get_full_name()) for member in super_members]
        supervisor_choices.insert(0, ('', '---------'))

        self.fields['supervisor'] = forms.ChoiceField(
            choices=supervisor_choices,
            widget=forms.Select(attrs={'class': 'form-control'}),
            label='Supervisor'
        )


class OtFormNoSup(forms.ModelForm):

    class Meta:
        model = Ot
        fields = ['description', 'system', 'state', 'tipo_mtto']
        labels = {
            'description': 'Descripción',
            'system': 'Sistema',
            'state': 'Estado',
            'tipo_mtto': 'Tipo de mantenimiento',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'tipo_mtto': forms.Select(attrs={'class': 'form-control'}),
            'system': forms.Select(attrs={'class': 'form-control'}),
            'state': forms.Select(attrs={'class': 'form-control'}),
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
        fields = ['news', 'finished',]
        labels = {
                'news': 'Novedades',
                }
        widgets = {
            'news': forms.Textarea,
        }

    def __init__(self, *args, **kwargs):
        super(FinishTask, self).__init__(*args, **kwargs)
        self.fields['finished'].widget.attrs.update({'class': 'btn-group-toggle', 'data-toggle': 'buttons'})
        self.fields['news'].required = True


class ActForm(forms.ModelForm):

    delete_images = forms.BooleanField(required=False, label='Eliminar imágenes')
    responsible = UserChoiceField(queryset=User.objects.all(), label='Responsable', widget=forms.Select(attrs={'class': 'form-control'}),)

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
        print("Usuarios disponibles para responsible:", users)

        self.fields['responsible'].queryset = users


class ActFormNoSup(forms.ModelForm):

    finished = forms.ChoiceField(
        choices=[(True, 'Sí'), (False, 'No')],
        widget=forms.RadioSelect,
        label='Finalizado',
        initial=False,
        required=False
    )

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
    responsible = UserChoiceField(queryset=User.objects.exclude(groups__name='gerencia'), label='Responsable', required=False, widget=forms.Select(attrs={'class': 'form-control'}))

    class Meta:
        model = Task
        fields = ['responsible', 'description', 'procedimiento', 'hse', 'priority', 'equipo']
        labels = {
            'description': 'Descripción',
            'procedimiento': 'Procedimiento',
            'hse': 'Precauciones de seguridad',
            'priority': 'Prioridad (entre mayor sea el numero tendra mas prioridad)',
            'equipo': 'Equipo',
            }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'procedimiento': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'hse': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'priority': forms.NumberInput(attrs={'class': 'form-control'}),
            'equipo': forms.Select(attrs={'class': 'form-control'}),
            }

    def __init__(self, *args, **kwargs):
        asset = kwargs.pop('asset')
        super().__init__(*args, **kwargs)
        self.fields['equipo'].queryset = Equipo.objects.filter(system__asset=asset)


# ---------------- Rutinas ------------------- #
class RutaForm(forms.ModelForm):

    def clean(self):
        cleaned_data = super().clean()
        control = cleaned_data.get('control')
        equipo = cleaned_data.get('equipo')

        if (control == 'h' or control == 'k') and not equipo:
            self.add_error(
                'equipo',
                'Seleccionar un equipo es obligatorio para el control en horas o kilometros'
                )
        return cleaned_data

    def clean_frecuency(self):
        frecuency = self.cleaned_data['frecuency']

        if frecuency < 0:
            raise forms.ValidationError('El valor de la frecuencia no puede ser 0.')
        return frecuency

    class Meta:
        model = Ruta
        exclude = ['system', 'astillero', 'modified_by']
        labels = {
            'name': 'Codigo interno',
            'frecuency': 'Frecuencia',
            'intervention_date': 'Fecha ultima intervención',
            'nivel': 'Convención',
            'dependencia': 'Dependencia',
            'ot': 'Ultima orden de trabajo relacionada',
            }
        widgets = {
            'intervention_date': XYZ_DateInput(format=['%Y-%m-%d'], attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'rows': 4, 'class': 'form-control'}),
            'control': forms.Select(attrs={'class': 'form-control'}),
            'equipo': forms.Select(attrs={'class': 'form-control'}),
            'frecuency': forms.NumberInput(attrs={'class': 'form-control'}),
            'ot': forms.Select(attrs={'class': 'form-control'}),
            'dependencia': forms.Select(attrs={'class': 'form-control'}),
            'nivel': forms.Select(attrs={'class': 'form-control'}),
            }

    def __init__(self, *args, **kwargs):
        system = kwargs.pop('system')
        super(RutaForm, self).__init__(*args, **kwargs)
        self.fields['equipo'].queryset = Equipo.objects.filter(system=system)
        self.fields['ot'].queryset = Ot.objects.filter(system__asset=system.asset)
        self.fields['dependencia'].queryset = Ruta.objects.filter(system=system).exclude(code=self.instance.code if self.instance else None)


# ---------------- Hours ------------------- #
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
        exclude = ['report', 'reporter', 'closed', 'evidence', 'modified_by', 'related_ot']
        labels = {
            'equipo': 'Equipo que presenta la falla',
            'description': 'Descripción detallada de falla presentada',
            'causas': 'Describa las causas probable de la falla',
            'suggest_repair': 'Reparación sugerida',
            }
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'causas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'suggest_repair': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super(failureForm, self).__init__(*args, **kwargs)
        if self.instance and self.instance.related_ot:
            # Agregar el campo 'related_ot' solo si ya tiene una OT asociada
            self.fields['related_ot'] = forms.ModelChoiceField(
                queryset=Ot.objects.filter(system=self.instance.equipo.system),
                required=False,
                label='Orden de Trabajo Asociada',
            )
            # Establecer el valor inicial
            self.fields['related_ot'].initial = self.instance.related_ot

    def clean(self):
        cleaned_data = super().clean()
        equipo = cleaned_data.get('equipo')

        if not equipo:
            self.add_error('equipo', 'El campo "Equipo que presenta la falla" es obligatorio.')

        return cleaned_data


# ---------------- Operaciones ------------------- #
class OperationForm(forms.ModelForm):

    confirmado = forms.ChoiceField(
        choices=[(True, 'Sí'), (False, 'No')],
        widget=forms.RadioSelect,
        label='Proyecto confirmado',
        initial=False,
        required=False
    )

    def __init__(self, *args, **kwargs):
        super(OperationForm, self).__init__(*args, **kwargs)
        self.fields['asset'].queryset = Asset.objects.filter(area='a')
        self.fields['confirmado'].widget.attrs.update({'class': 'btn-group-toggle', 'data-toggle': 'buttons'})

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start')
        end = cleaned_data.get('end')
        asset = cleaned_data.get('asset')
        confirmado = cleaned_data.get('confirmado')

        if start and end and start > end:
            raise ValidationError({
                'start': 'La fecha de inicio no puede ser posterior a la fecha de fin.',
                'end': 'La fecha de fin no puede ser anterior a la fecha de inicio.'
            })

        if not confirmado and start and end and asset:
            overlapping_operations = Operation.objects.filter(
                asset=asset,
                end__gte=start,
                start__lte=end,
                confirmado=False
            )
            if self.instance.pk:
                overlapping_operations = overlapping_operations.exclude(pk=self.instance.pk)

            if overlapping_operations.exists():
                raise ValidationError('Existe un conflicto entre las fechas seleccionadas.')

        return cleaned_data

    class Meta:
        model = Operation
        fields = ['proyecto', 'asset', 'start', 'end', 'confirmado']# , 'requirements'
        widgets = {
            'start': XYZ_DateInput(format=['%Y-%m-%d'],),
            'end': XYZ_DateInput(format=['%Y-%m-%d'],),
            # 'requirements': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'asset': 'Equipo',
            'proyecto': 'Nombre del Proyecto',
            'start': 'Fecha de Inicio',
            'end': 'Fecha de Fin',
            # 'requirements': 'Requerimientos',
        }


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['description', 'file']
        widgets = {
            'description':forms.TextInput(attrs={'class': 'form-control'}),
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
        instance = kwargs.get('instance', None)

        if user and user.is_authenticated:
            self.fields['nombre_no_registrado'].widget = forms.HiddenInput()
        else:
            self.fields['nombre_no_registrado'].required = True

        if instance:
            # Prellenar 'nuevo_kilometraje' con el valor existente
            self.fields['nuevo_kilometraje'].initial = instance.kilometraje

    def clean_nuevo_kilometraje(self):
        nuevo_kilometraje = self.cleaned_data.get('nuevo_kilometraje')
        if self.equipo:
            if self.instance.pk:
                pass
            else:
                # Modo creación
                if nuevo_kilometraje < self.equipo.horometro:
                    raise forms.ValidationError("El nuevo kilometraje debe ser igual o mayor al kilometraje actual.")
        return nuevo_kilometraje
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Si el campo está deshabilitado, mantener el valor original
        if self.fields['nombre_no_registrado'].widget.__class__ == forms.HiddenInput:
            instance.nombre_no_registrado = self.initial.get('nombre_no_registrado', instance.nombre_no_registrado)
        if commit:
            instance.save()
        return instance


class TransferenciaForm(forms.ModelForm):
    destino = forms.ModelChoiceField(
        queryset=System.objects.all().select_related('asset').order_by('asset__name', 'name'),
        label="Sistema Destino",
        required=True
    )
    observaciones = forms.CharField(widget=forms.Textarea, label="Justificación", required=False)

    class Meta:
        model = Transferencia
        fields = ['destino', 'observaciones']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['destino'].label_from_instance = lambda obj: f"{obj.asset.name} - {obj.name}"


class DarBajaForm(forms.ModelForm):

    class Meta:
        model = DarBaja
        fields = ['motivo', 'observaciones', 'disposicion', 'firma_responsable', 'firma_autorizado']


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['name', 'reference', 'presentacion', 'code', 'seccion', 'imagen']
        labels = {
            'name': 'Articulo',
            'reference': 'Referencia',
            'presentacion': 'Presentación',
            'code': 'Codigo Zeus',
            'seccion': 'Categoria'
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'presentacion': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'seccion': forms.Select(attrs={'class': 'form-control'}),
            'imagen': ClearableFileInput(attrs={'class': 'form-control'}),
        }


class ActivityForm(forms.Form):
    realizado = forms.BooleanField(required=False, label='Realizado')
    observaciones = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-class'}))

class CustomSignatureForm(forms.Form):
    signature = forms.CharField(widget=forms.HiddenInput())


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
        labels = {
            'motivo': 'Motivo de la baja',
            'observaciones': 'Observaciones',
            'disposicion': 'Disposición final del equipo',
            'responsable': 'Responsable del equipo',
        }


class RequirementForm(forms.ModelForm):
    approved = forms.ChoiceField(
        choices=[(True, 'Sí'), (False, 'No')],
        widget=forms.RadioSelect,
        label='Realizado',
        initial=False,
        required=False
    )
    class Meta:
        model = Requirement
        fields = ['text', 'responsable']  # Incluimos 'responsable'
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control'}),
            'responsable': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'text': 'Detalle del requerimiento',
            'responsable': 'Responsable',
        }


class FullRequirementForm(forms.ModelForm):
    approved = forms.ChoiceField(
        choices=[(True, 'Sí'), (False, 'No')],
        widget=forms.RadioSelect,
        label='Realizado',
        initial=False,
        required=False
    )
    class Meta:
        model = Requirement
        fields = ['text', 'responsable', 'approved', 'novedad']
        widgets = {
            'text': forms.Textarea(attrs={'class': 'form-control'}),
            'responsable': forms.TextInput(attrs={'class': 'form-control'}),
            'novedad': forms.Textarea(attrs={'class': 'form-control'}),
        }
        labels = {
            'text': 'Detalle del requerimiento',
            'responsable': 'Responsable',
            'novedad': 'Novedad',
        }


class LimitedRequirementForm(forms.ModelForm):
    approved = forms.ChoiceField(
        choices=[(True, 'Sí'), (False, 'No')],
        widget=forms.RadioSelect,
        label='Realizado',
        initial=False,
        required=False
    )
    class Meta:
        model = Requirement
        fields = ['novedad', 'approved']
        widgets = {
            'novedad': forms.Textarea(attrs={'class': 'form-control'}),
        }
        labels = {
            'novedad': 'Novedad',
        }


class EquipmentHistoryForm(forms.ModelForm):
    class Meta:
        model = EquipmentHistory
        fields = ['date', 'subject', 'annotations']
        labels = {
            'date': 'Fecha',
            'subject': 'Asunto',
            'annotations': 'Anotaciones'          
        }
        widgets = {
            'date': XYZ_DateInput(format=['%Y-%m-%d'],),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'annotations': forms.Textarea(attrs={'class': 'form-control'}),
        }


class MaintenanceRequirementForm(forms.ModelForm):
    class Meta:
        model = MaintenanceRequirement
        fields = ['item', 'descripcion', 'tipo', 'cantidad']
        labels = {
            'item': 'Artículo',
            'descripcion': 'Descripción',
            'tipo': 'Tipo',
            'cantidad': 'Cantidad',
        }
        widgets = {
            'item': forms.Select(attrs={'class': 'form-control'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control'}),
        }