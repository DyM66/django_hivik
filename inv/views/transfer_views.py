from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View

from got.models import Equipo, Ruta
from got.utils import pdf_render
from inv.models.inventory import Transference
from inv.forms import TransferenciaForm
from inv.utils import enviar_correo_transferencia


@login_required
def transferir_equipo(request, equipo_id):
    equipo = get_object_or_404(Equipo, pk=equipo_id)  # Equipo a trasladar
    next_url = request.GET.get('next') or request.POST.get('next') or None
    related_equipos = equipo.related_with.all()

    if request.method == 'POST':
        form = TransferenciaForm(request.POST)
        transfer_related_ids = request.POST.getlist('transfer_related')
        if form.is_valid():
            nuevo_sistema = form.cleaned_data['destino']
            observaciones = form.cleaned_data['observaciones']
            receptor = form.cleaned_data['receptor']

            sistema_origen = equipo.system      
            equipo.system = nuevo_sistema  # Actualiza el sistema del equipo principal   
            equipo.save()

            rutas = Ruta.objects.filter(equipo=equipo)  # Actualiza las rutas asociadas al equipo
            for ruta in rutas:
                ruta.system = nuevo_sistema
                ruta.save()

            transferred_related_names = []  # Procesa los equipos relacionados
            for rel in related_equipos:
                if str(rel.code) in transfer_related_ids:
                    rel.system = nuevo_sistema  # Se transfiere el equipo relacionado
                    rel.save()
                    transferred_related_names.append(rel.name)
                else:
                    rel.related = None  # Se rompe la relación (se desvincula)
                    rel.save()

            # Anexa la lista de equipos relacionados transferidos a las observaciones
            if transferred_related_names:
                observaciones += "\nEquipos relacionados transferidos: " + ", ".join(transferred_related_names)

            # Crea el registro de Transferencia
            transferencia = Transference.objects.create(
                equipo=equipo,
                responsable=f"{request.user.first_name} {request.user.last_name}",
                receptor=receptor,
                origen=sistema_origen,
                destino=nuevo_sistema,
                observaciones=observaciones
            )

            enviar_correo_transferencia(transferencia, equipo, sistema_origen, nuevo_sistema, observaciones)
            messages.success(request, "Transferencia realizada exitosamente.")
            if next_url:
                return redirect(next_url)
            else:
                return redirect(sistema_origen.get_absolute_url())
    else:
        form = TransferenciaForm()

    context = {
        'form': form,
        'equipo': equipo,
        'related_equipos': related_equipos,
        'next_url': next_url
    }
    return render(request, 'inventory_management/transferencias.html', context)

class TransferPDFView(LoginRequiredMixin, View):
    def get(self, request, pk, *args, **kwargs):
        transfer = get_object_or_404(Transference, pk=pk)

        context = {
            'transfer': transfer
        }
        return pdf_render(request, 'inventory_management/pdf_templates/transfer_document.html', context, "ACTA_DE_TRANSFERENCIA_EQUIPOS.pdf")