from django import forms
from .models import *

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
            'pi_obs_l1_tierra': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'pi_obs_l2_tierra': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'pi_obs_l3_tierra': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'pi_obs_l1_l2': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'pi_obs_l2_l3': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'pi_obs_l3_l1': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ExcitatrizForm(forms.ModelForm):
    class Meta:
        model = Excitatriz
        exclude = ['megger']

        widgets = {
                'pi_1min_l_tierra' : forms.TextInput(attrs={'class': 'form-control'}), 
                'pi_10min_l_tierra' : forms.TextInput(attrs={'class': 'form-control'}),
                'pi_obs_l_tierra' : forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
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