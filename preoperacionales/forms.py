from django import forms
from got.models import Equipo
from .models import *
from django.core.exceptions import ValidationError


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
        required=True,
    )

    aseo_externo = forms.ChoiceField(
        choices=choices_aseo,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='Aseo externo',
        required=True,
    )

    aseo_interno = forms.ChoiceField(
        choices=choices_aseo,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='Aseo interno',
        required=True,
    )

    kit_carreteras = forms.ChoiceField(
        choices=choices_completo,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='Kit de carreteras',
        required=True,
    )
    
    kit_herramientas = forms.ChoiceField(
        choices=choices_completo,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='Kit de herramientas',
        required=True,
    )

    kit_botiquin = forms.ChoiceField(
        choices=choices_completo,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='Kit de botiquín',
        required=True,
    )

    chaleco_reflectivo = forms.ChoiceField(
        choices=choices,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='IMPLEMENTOS DE SEGURIDAD VIAL ¿Tiene chalecos reflectivos?',
        required=True,
    )

    aprobado = forms.ChoiceField(
        choices=choices_aprobado,
        widget=forms.RadioSelect(attrs={'class': 'btn-group-toggle', 'data-toggle': 'buttons'}),
        label='CERTIFICO QUE EL VEHÍCULO INSPECCIONADO ESTÁ ADECUADO PARA SER UTILIZADO DURANTE EL DÍA DE LA INSPECCIÓN REALIZADA:',
        required=True,
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

        for field_name, field in self.fields.items():
            field.required = True  
            field.initial = None   
            if(field_name == 'nombre_no_registrado' or field_name == 'observaciones'):
                field.required = False


        instance = kwargs.get('instance', None)
        if instance and instance.nombre_no_registrado:
            self.fields['nombre_no_registrado'].disabled = True
            self.fields['nombre_no_registrado'].required = False 

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Si el campo está deshabilitado, asegurarse de mantener el valor original
        if self.fields['nombre_no_registrado'].disabled:
            instance.nombre_no_registrado = self.initial.get('nombre_no_registrado', instance.nombre_no_registrado)
        if commit:
            instance.save()
        return instance

    def clean_kilometraje(self):
        kilometraje = self.cleaned_data.get('kilometraje')
        if self.instance.pk is None:
            if kilometraje < self.equipo.horometro:
                raise ValidationError("[!] El nuevo kilometraje debe ser igual o mayor al kilometraje actual del vehículo.")

        return kilometraje
    

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
    

# class PreoperacionalForm(forms.ModelForm):
#     vehiculo = forms.ModelChoiceField(queryset=System.objects.filter(asset__area='v'), empty_label="Seleccione un Vehículo", widget=forms.Select(attrs={'class': 'form-control'}))
#     nuevo_kilometraje = forms.IntegerField(label="Kilometraje Actual", required=True, widget=forms.NumberInput(attrs={'class': 'form-control'}))

#     class Meta:
#         model = Preoperacional
#         fields = ['nombre_no_registrado', 'cedula', 'motivo', 'salida', 'destino', 'tipo_ruta', 'autorizado', 'observaciones', 'vehiculo', 'nuevo_kilometraje']
#         labels = {
#             'nombre_no_registrado': 'Nombre y apellido del solicitante',
#             'cedula': 'Cédula del solicitante',
#             'motivo': 'Motivo del desplazamiento',
#             'salida': 'Punto de salida',
#             'destino': 'Destino',
#             'tipo_ruta': 'Tipo de ruta',
#             'autorizado': 'Autorizado por',
#             'Observaciones': 'HALLAZGOS ENCONTRADOS EN EL VEHÍCULO ANTES DE LA SALIDA (En esta sección se deberá remitir evidencia de inconsistencias encontradas en el vehículo antes de la salida de las instalaciones de SERPORT).',
#         }
#         widgets = {
#                 'nombre_no_registrado' : forms.TextInput(attrs={'class': 'form-control'}), 
#                 'cedula' : forms.TextInput(attrs={'class': 'form-control'}),
#                 'motivo' : forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
#                 'salida' : forms.TextInput(attrs={'class': 'form-control'}), 
#                 'destino' : forms.TextInput(attrs={'class': 'form-control'}), 
#                 'tipo_ruta': forms.Select(attrs={'class': 'form-control'}),
#                 'autorizado': forms.Select(attrs={'class': 'form-control'}),
#                 'observaciones' : forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
#         }

#     def __init__(self, *args, **kwargs):
#         user = kwargs.pop('user', None)
#         super(PreoperacionalForm, self).__init__(*args, **kwargs)
#         if user and user.is_authenticated:
#             self.fields['nombre_no_registrado'].widget = forms.HiddenInput()
#         else:
#             self.fields['nombre_no_registrado'].required = True
#         self.fields['vehiculo'].queryset = System.objects.filter(asset__area='v')

