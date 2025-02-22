import calendar

from django.utils import timezone
from django import forms

from got.models import System

class RutinaFilterForm(forms.Form):
    current_year = timezone.now().year
    max_year = current_year + 5

    MONTH_CHOICES = [(i, calendar.month_name[i].capitalize()) for i in range(1, 13)]
    YEAR_CHOICES = [(i, str(i)) for i in range(current_year, max_year + 1)]

    month = forms.ChoiceField(choices=MONTH_CHOICES, initial=timezone.now().month   , label="Mes", widget=forms.Select(attrs={'class': 'form-control'}),)
    year = forms.ChoiceField(choices=YEAR_CHOICES, initial=timezone.now().month, label="Año", widget=forms.Select(attrs={'class': 'form-control'}),)
    # execute = forms.BooleanField(required=False, initial=False, label="Mostrar rutinas en ejecución", widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),)

    def __init__(self, *args, **kwargs):
        asset = kwargs.pop('asset', None)
        super().__init__(*args, **kwargs)

        print(timezone.now())
        if asset:
            systems = asset.system_set.all().distinct()
            other_asset_systems = System.objects.filter(location=asset.name).exclude(asset=asset).distinct()
            full_systems = systems.union(other_asset_systems)
            locations = full_systems.values_list('location', flat=True)
            unique_locations = list(set(locations))  # Eliminar duplicados
            location_choices = [(location, location) for location in unique_locations]
            self.fields['locations'] = forms.MultipleChoiceField(choices=location_choices, widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}), initial=[location for location in unique_locations], required=False, label="Ubicaciones")
