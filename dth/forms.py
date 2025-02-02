from django import forms
from django.contrib.auth.models import User
from dth.models import UserProfile


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        label='Nombre',
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu nombre'})
    )
    last_name = forms.CharField(
        label='Apellido',
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu apellido'})
    )
    email = forms.EmailField(
        label='Correo electrónico',
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': '@serport.co'})
    )

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
        # Recibimos la instancia del usuario para personalizar el formulario si fuera necesario
        self.user = kwargs.pop('user', None)
        super(UserProfileForm, self).__init__(*args, **kwargs)
