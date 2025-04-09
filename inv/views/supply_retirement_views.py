# inv/views/supply_retirement_views.py
import base64
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView
from django.utils import timezone

from inv.models.inventory import Suministro
from inv.models.equipment_retirement import RetiredSupply, RetiredSupplyImage
from inv.models import Transaction
from inv.forms import RetiredSupplyForm
from inv.forms.retirement_forms import UploadEvidenciasYFirmasForm


class RetireSupplyCreateView(LoginRequiredMixin, CreateView):
    model = RetiredSupply
    form_class = RetiredSupplyForm
    template_name = 'inventory_management/retirement_supply_form.html'

    def get_suministro(self):
        pk = self.kwargs.get('pk')
        return get_object_or_404(Suministro, id=pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        suministro = self.get_suministro()
        ctx['suministro'] = suministro
        # Form para las evidencias y firmas
        if self.request.method == 'POST':
            ctx['upload_form'] = UploadEvidenciasYFirmasForm(
                self.request.POST, 
                self.request.FILES
            )
        else:
            ctx['upload_form'] = UploadEvidenciasYFirmasForm()
        return ctx

    def form_valid(self, form):
        suministro = self.get_suministro()
        user = self.request.user

        # 1) Validar que la cantidad no supere lo disponible
        cantidad_retirada = form.cleaned_data['amount']
        if cantidad_retirada > suministro.cantidad:
            messages.error(self.request, "La cantidad a dar de baja excede lo disponible.")
            return self.form_invalid(form)

        # 2) Validar el segundo formulario (upload_form)
        upload_form = self.get_context_data()['upload_form']
        if not upload_form.is_valid():
            messages.error(self.request, "Error en formulario de evidencias/firmas.")
            return self.form_invalid(form)

        # 1) Asignar campos que no vienen en el form
        retired_supply = form.save(commit=False)
        retired_supply.supply = suministro
        retired_supply.user = user
        retired_supply.date = timezone.now().date()
        retired_supply.save()  # Se guarda la instancia
        self.object = retired_supply

        # 3) Procesar firmas (si usas la lógica base64 => revisa tu approach de DarBaja)
        firma_resp_file = upload_form.cleaned_data.get('firma_responsable_file')
        firma_aut_file = upload_form.cleaned_data.get('firma_autorizado_file')

        firma_resp_data = self.request.POST.get('firma_responsable_data', '')
        firma_aut_data = self.request.POST.get('firma_autorizado_data', '')

        # Si no se subió archivo, chequeamos el canvas base64, etc.
        if firma_resp_file:
            if not firma_resp_file.content_type.startswith('image/'):
                messages.error(self.request, "Archivo de firma responsable no es válido.")
                retired_supply.delete()
                return self.form_invalid(form)
            retired_supply.responsible_signature = firma_resp_file
            retired_supply.save(update_fields=['responsible_signature'])
        else:
            # Canvas base64
            if firma_resp_data:
                self.save_base64_firma(retired_supply, firma_resp_data, field='responsible_signature')

        if firma_aut_file:
            if not firma_aut_file.content_type.startswith('image/'):
                messages.error(self.request, "Archivo de firma autorizado no es válido.")
                retired_supply.delete()
                return self.form_invalid(form)
            retired_supply.authorized_signature = firma_aut_file
            retired_supply.save(update_fields=['authorized_signature'])
        else:
            if firma_aut_data:
                self.save_base64_firma(retired_supply, firma_aut_data, field='authorized_signature')

        # 4) Guardar imágenes de evidencia
        evidence_files = upload_form.cleaned_data['file_field']  # lista de archivos
        for file_obj in evidence_files:
            if not file_obj.content_type.startswith('image/'):
                messages.error(self.request, "Uno de los archivos de evidencia no es una imagen válida.")
                retired_supply.delete()
                return self.form_invalid(form)
            RetiredSupplyImage.objects.create(
                image=file_obj, 
                retired_supply=retired_supply
            )

        # 5) Descontar la cantidad en el Suministro
        suministro.cantidad -= cantidad_retirada
        suministro.save(update_fields=['cantidad'])

        # 6) Crear la Transaction de tipo 'r'
        Transaction.objects.create(
            suministro=suministro,
            cant=cantidad_retirada,
            fecha=retired_supply.date,
            user=user.get_full_name() or user.username,
            motivo=f"Baja: {retired_supply.get_reason_display()} - {retired_supply.remark}",
            tipo='r',
            cant_report=suministro.cantidad,
            retired_supply = retired_supply 
        )

        messages.success(self.request, "Se ha dado de baja este suministro correctamente.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        """Redirigir de vuelta al inventario del asset correspondiente."""
        asset_abbr = self.object.supply.asset.abbreviation
        return reverse('inv:asset_inventario_report', kwargs={'abbreviation': asset_abbr})

    def save_base64_firma(self, obj, base64_data, field='responsible_signature'):
        """Helper para guardar la firma en ImageField a partir de base64."""
        try:
            fmt, imgstr = base64_data.split(';base64,')
            ext = fmt.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr))
            filename = f"{field}_{obj.pk}.{ext}"
            getattr(obj, field).save(filename, data, save=True)
        except:
            pass
