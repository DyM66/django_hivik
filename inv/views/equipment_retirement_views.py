from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import CreateView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.core.files.base import ContentFile
from django.urls import reverse

import base64

from got.models import Equipo, Image, System
from got.utils import render_to_pdf
from inv.models.others import DarBaja
from inv.forms import DarBajaForm, UploadEvidenciasYFirmasForm

class DarBajaCreateView(LoginRequiredMixin, CreateView):
    model = DarBaja
    form_class = DarBajaForm
    template_name = 'inventory_management/dar_baja_form.html'

    def get_equipo(self):
        equipo_code = self.kwargs['equipo_code']
        return get_object_or_404(Equipo, code=equipo_code)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        equipo = self.get_equipo()
        context['equipo'] = equipo

        if self.request.method == 'POST':  # Instanciar el segundo formulario (evidencias + firmas)
            context['upload_form'] = UploadEvidenciasYFirmasForm(self.request.POST, self.request.FILES)
        else:
            context['upload_form'] = UploadEvidenciasYFirmasForm()
        return context

    def form_valid(self, form):
        equipo = self.get_equipo()
        user = self.request.user
        form.instance.equipo = equipo
        form.instance.reporter = user.get_full_name() or user.username
        form.instance.activo = f"{equipo.system.asset.name} - {equipo.system.name}"

        # Guardamos de forma normal
        response = super().form_valid(form)

        # 2) Procesar upload_form
        upload_form = self.get_context_data()['upload_form']
        if not upload_form.is_valid():
            messages.error(self.request, "Error en el formulario de subida de archivos.")
            self.object.delete()
            return self.form_invalid(form)

        # Tomar subidas de firma
        fr_file = upload_form.cleaned_data.get('firma_responsable_file')
        fa_file = upload_form.cleaned_data.get('firma_autorizado_file')

        # Tomar data base64 de canvas
        firma_responsable_data = self.request.POST.get('firma_responsable_data', '')
        firma_autorizado_data = self.request.POST.get('firma_autorizado_data', '')

        # Chequeo => O suben archivo o dibujan la firma
        if not fr_file and not firma_responsable_data:
            messages.error(self.request, "Debe proporcionar la firma Responsable (archivo o dibujo).")
            self.object.delete()
            return self.form_invalid(form)

        if not fa_file and not firma_autorizado_data:
            messages.error(self.request, "Debe proporcionar la firma Autorizado (archivo o dibujo).")
            self.object.delete()
            return self.form_invalid(form)

        # Firma Responsable
        if fr_file:
            if not fr_file.content_type.startswith('image/'):
                messages.error(self.request, "Archivo de firma responsable no es válido.")
                self.object.delete()
                return self.form_invalid(form)
            self.object.firma_responsable = fr_file
            self.object.save(update_fields=['firma_responsable'])
        else:
            # Canvas base64
            fmt, imgstr = firma_responsable_data.split(';base64,')
            ext = fmt.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr))
            self.object.firma_responsable.save(f'firma_responsable_{self.object.pk}.{ext}', data, save=True)

        # Firma Autorizado
        if fa_file:
            if not fa_file.content_type.startswith('image/'):
                messages.error(self.request, "Archivo de firma autorizado no es válido.")
                self.object.delete()
                return self.form_invalid(form)
            self.object.firma_autorizado = fa_file
            self.object.save(update_fields=['firma_autorizado'])
        else:
            fmt, imgstr = firma_autorizado_data.split(';base64,')
            ext = fmt.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr))
            self.object.firma_autorizado.save(f'firma_autorizado_{self.object.pk}.{ext}', data, save=True)

        # 3) Evidencias => multiple
        evidences = upload_form.cleaned_data['file_field']  # lista de archivos
        for file_obj in evidences:
            if not file_obj.content_type.startswith('image/'):
                messages.error(self.request, "Uno de los archivos de evidencia no es una imagen válida.")
                self.object.delete()
                return self.form_invalid(form)
            Image.objects.create(image=file_obj, darbaja=self.object)

        # 4) Eliminar rutinas/hours/etc
        self.do_equipo_cleanup(equipo)

        # 5) Mover equipo a system 445
        new_system = System.objects.get(id=445)
        old_system = equipo.system
        equipo.system = new_system
        equipo.save()
        messages.success(self.request, f'El equipo ha sido trasladado al sistema {new_system.name}.')

        # 6) Generar PDF (opcional)
        self.generate_pdf()
        return redirect(self.get_success_url())  # 7) Redirigir => 'activos/<str:abbreviation>/equipos/'

    def do_equipo_cleanup(self, equipo):
        # Eliminar rutinas, hours, etc.
        ...
        # (Idéntico a tu lógica actual)

    def generate_pdf(self):
        context = {
            'dar_baja': self.object,
            'equipo': self.object.equipo
        }
        pdf = render_to_pdf('inventory_management/dar_baja_pdf.html', context)
        if pdf:
            # Podrías guardarlo en disco, o en la base de datos, 
            # o ignorarlo si solo deseas generarlo internamente
            filename = f'dar_baja_{self.object.pk}.pdf'
            # Ejemplo: guardarlo en un directorio local (opcional)
            # with open(f'/tmp/{filename}', 'wb') as f:
            #     f.write(pdf.getvalue())
        else:
            messages.warning(self.request, 'No se pudo generar el PDF.')

    def get_success_url(self):
        # Redirigir a: path('activos/<str:abbreviation>/equipos/', name='asset_equipment_list'),
        # old_system.asset.abbreviation => => 'inv:asset_equipment_list'
        abbreviation = self.object.equipo.system.asset.abbreviation
        return reverse('inv:asset_equipment_list', kwargs={'abbreviation': abbreviation})

