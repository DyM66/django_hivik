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
        kilometraje = self.cleaned_data['kilometraje']
        if self.instance.pk is None:
            if kilometraje < self.equipo.horometro:
                raise ValidationError("El nuevo kilometraje debe ser igual o mayor al kilometraje actual del vehículo.")

        return kilometraje