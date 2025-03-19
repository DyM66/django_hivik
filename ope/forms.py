# ---------------- Operaciones ------------------- #
from django import forms
from django.core.exceptions import ValidationError
from got.models import Asset
from .models import Operation
from got.forms import XYZ_DateInput


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
        # self.fields['asset'].queryset = Asset.objects.filter(area='a')
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
        fields = ['proyecto','start','end','requirements', 'confirmado']
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