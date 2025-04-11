from django import forms
from got.models import Equipo
from preoperacionales.models import *


class PreoperacionalEspecificoForm(forms.ModelForm):
    choices = [
        (True, "Sí"),
        (False, "No"),
    ]

    choices_reporte = [
        (True, "Si, reportar falla"),
        (False, "No, solo dejar constancia"),
    ]

    horas_trabajo = forms.ChoiceField(
        choices=choices,
        widget=forms.RadioSelect(
            attrs={"class": "btn-group-toggle", "data-toggle": "buttons"}
        ),
        label="¿Las horas de trabajo más las horas de conducción superan 12 horas?",
        required=True,
    )

    medicamentos = forms.ChoiceField(
        choices=choices,
        widget=forms.RadioSelect(
            attrs={"class": "btn-group-toggle", "data-toggle": "buttons"}
        ),
        label="¿Ha ingerido medicamentos que inducen sueño durante el día u horas previas a la jornada laboral?",
        required=True,
    )

    molestias = forms.ChoiceField(
        choices=choices,
        widget=forms.RadioSelect(
            attrs={"class": "btn-group-toggle", "data-toggle": "buttons"}
        ),
        label="¿Ha consultado al médico o asistido a urgencias por alguna molestia que le dificulte conducir?",
        required=True,
    )

    enfermo = forms.ChoiceField(
        choices=choices,
        widget=forms.RadioSelect(
            attrs={"class": "btn-group-toggle", "data-toggle": "buttons"}
        ),
        label="¿Se encuentra enfermo o con alguna condición que le impida conducir?",
        required=True,
    )

    condiciones = forms.ChoiceField(
        choices=choices,
        widget=forms.RadioSelect(
            attrs={"class": "btn-group-toggle", "data-toggle": "buttons"}
        ),
        label="¿Se siente en condiciones para conducir en la jornada asignada?",
        required=True,
    )

    agua = forms.ChoiceField(
        choices=choices,
        widget=forms.RadioSelect(
            attrs={"class": "btn-group-toggle", "data-toggle": "buttons"}
        ),
        label="¿Tiene agua para beber?",
        required=True,
    )

    dormido = forms.ChoiceField(
        choices=choices,
        widget=forms.RadioSelect(
            attrs={"class": "btn-group-toggle", "data-toggle": "buttons"}
        ),
        label="¿Ha dormido al menos 8 horas en las últimas 24 horas?",
        required=True,
    )

    control = forms.ChoiceField(
        choices=choices,
        widget=forms.RadioSelect(
            attrs={"class": "btn-group-toggle", "data-toggle": "buttons"}
        ),
        label="¿Conoce los puestos de control en la vía? (Planifico e identifico los lugares de descanso)",
        required=True,
    )

    sueño = forms.ChoiceField(
        choices=choices,
        widget=forms.RadioSelect(
            attrs={"class": "btn-group-toggle", "data-toggle": "buttons"}
        ),
        label="¿En caso de sentir sueño sabe qué hacer?",
        required=True,
    )

    radio_aire = forms.ChoiceField(
        choices=choices,
        widget=forms.RadioSelect(
            attrs={"class": "btn-group-toggle", "data-toggle": "buttons"}
        ),
        label="¿El vehículo que conduce tiene radio y aire acondicionado?",
        required=True,
    )

    nuevo_kilometraje = forms.IntegerField(
        label="Kilometraje Actual",
        required=True,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    authorized = forms.ModelChoiceField(
        queryset=Authorizer.objects.all(),
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Autorizado por",
        required=True,
    )

    wants_to_report_failure = forms.ChoiceField(
        choices=choices_reporte,
        widget=forms.RadioSelect(attrs={"class": "", "data-toggle": ""}),
        label="Quieres registrar los hallazgos en un reporte de falla? (SOLO SI ES CRITICO)",
        required=True,
    )

    class Meta:
        model = Preoperacional
        fields = [
            "nombre_no_registrado",
            "cedula",
            "nuevo_kilometraje",
            "motivo",
            "salida",
            "destino",
            "tipo_ruta",
            "authorized",
            "observaciones",
            "horas_trabajo",
            "medicamentos",
            "molestias",
            "enfermo",
            "condiciones",
            "agua",
            "dormido",
            "control",
            "sueño",
            "radio_aire",
        ]
        labels = {
            "nombre_no_registrado": "Nombre y apellido del solicitante",
            "cedula": "Cédula del solicitante",
            "motivo": "Motivo del desplazamiento",
            "salida": "Punto de salida",
            "destino": "Destino",
            "tipo_ruta": "Tipo de ruta",
            "authorized": "Autorizado por",
            "observaciones": "HALLAZGOS ENCONTRADOS EN EL VEHÍCULO ANTES DE LA SALIDA (En esta sección se deberá remitir evidencia de inconsistencias encontradas en el vehículo antes de la salida de las instalaciones de SERPORT).",
        }
        widgets = {
            "nombre_no_registrado": forms.TextInput(attrs={"class": "form-control"}),
            "cedula": forms.TextInput(attrs={"class": "form-control"}),
            "motivo": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "salida": forms.TextInput(attrs={"class": "form-control"}),
            "destino": forms.TextInput(attrs={"class": "form-control"}),
            "tipo_ruta": forms.Select(attrs={"class": "form-control"}),
            "authorized": forms.Select(attrs={"class": "form-control"}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "wants_to_report_failure": forms.RadioSelect(
                attrs={"class": "btn-group-toggle", "data-toggle": "buttons"}
            ),
        }

    def __init__(self, *args, **kwargs):
        equipo_code = kwargs.pop("equipo_code", None)
        user = kwargs.pop("user", None)
        super(PreoperacionalEspecificoForm, self).__init__(*args, **kwargs)
        self.equipo = Equipo.objects.filter(code=equipo_code).first()
        instance = kwargs.get("instance", None)

        if user and user.is_authenticated:
            self.fields["nombre_no_registrado"].widget = forms.HiddenInput()
        else:
            self.fields["nombre_no_registrado"].required = True

        for name, field in self.fields.items():
            existing_classes = field.widget.attrs.get("class", "")
            # Solo agregamos 'is-invalid' si el campo tiene errores después del binding
            if self.errors.get(name):
                if "is-invalid" not in existing_classes:
                    field.widget.attrs["class"] = f"{existing_classes} is-invalid"
            else:
                field.widget.attrs["class"] = existing_classes

        if instance:
            # Prellenar 'nuevo_kilometraje' con el valor existente
            self.fields["nuevo_kilometraje"].initial = instance.kilometraje

    def clean_cedula(self):
        cedula = self.cleaned_data.get("cedula")
        driver_ids = Driver.objects.values_list("id_number", flat=True)

        if cedula not in driver_ids:
            raise forms.ValidationError(
                "La cédula ingresada no corresponde a un conductor registrado."
            )

        return cedula

    def clean_nuevo_kilometraje(self):
        nuevo_kilometraje = self.cleaned_data.get("nuevo_kilometraje")
        if self.equipo:
            if self.instance.pk:
                pass
            else:
                # Modo creación
                if nuevo_kilometraje < self.equipo.horometro:
                    raise forms.ValidationError(
                        "El nuevo kilometraje debe ser igual o mayor al kilometraje actual."
                    )
        return nuevo_kilometraje

    def clean_observaciones(self):
        cleaned_data = super().clean()
        observaciones = cleaned_data.get("observaciones")
        wants_to_report_failure = self.data.get("wants_to_report_failure")

        if wants_to_report_failure == "True" and not observaciones:
            self.add_error(
                "observaciones",
                "[!] Debes ingresar observaciones si deseas reportar una falla crítica. No olvides adjuntar evidencias.",
            )

        return observaciones

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Si el campo está deshabilitado, mantener el valor original
        if self.fields["nombre_no_registrado"].widget.__class__ == forms.HiddenInput:
            instance.nombre_no_registrado = self.initial.get(
                "nombre_no_registrado", instance.nombre_no_registrado
            )
        if commit:
            instance.save()  # Asegúrate de guardar la instancia
        return instance
