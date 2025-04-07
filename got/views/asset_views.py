from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import generic
from django.db import models
from django.db.models import Count
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib import messages

from got.models import Asset, System
from inv.models import Suministro
from got.forms import SysForm
from inv.utils.supplies_utils import supplies_summary
from outbound.models import Place
from ope.models import Operation


TODAY = timezone.now().date()
AREAS = {
    'a': 'Barcos',
    'c': 'Barcazas',
    'o': 'Oceanografía',
    'l': 'Locativo',
    'v': 'Vehiculos',
    'x': 'Apoyo',
}


class AssetsListView(LoginRequiredMixin, generic.TemplateView):
    template_name = 'got/assets/asset_list.html'

    def dispatch(self, request, *args, **kwargs):
        """Redirecciones personalizadas según el grupo del usuario."""
        user = request.user
        if user.groups.filter(name__in=['maq_members', 'buzos_members']).exists():
            asset = Asset.objects.filter(models.Q(supervisor=request.user) | models.Q(capitan=request.user)).first()
            if asset:
                return redirect('got:asset-detail', pk=asset.abbreviation)
        elif user.groups.filter(name='serport_members').exists():
            return redirect('got:my-tasks')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assets = Asset.objects.filter(show=True).annotate(
                total_failures_open=Count('system__equipos__failurereport', filter=models.Q(system__equipos__failurereport__closed=False), distinct=True),
                total_failures_process=Count('system__equipos__failurereport', filter=models.Q(system__equipos__failurereport__closed=False, system__equipos__failurereport__related_ot__isnull=False), distinct=True),
                total_ots_execution=Count('system__ot', filter=models.Q(system__ot__state='x'), distinct=True)
            ).order_by('area', 'name')

        for asset in assets:
            current_ops = Operation.objects.filter(asset=asset, start__lte=TODAY, end__gte=TODAY).order_by('start')

            if current_ops.exists():
                operation = current_ops.first()
                asset.operation_name = operation.proyecto
                asset.is_current_operation = True
            else:
                upcoming_ops = Operation.objects.filter(asset=asset, start__gt=TODAY).order_by('start')

                if upcoming_ops.exists():
                    operation = upcoming_ops.first()
                    asset.operation_name = operation.proyecto
                    asset.is_current_operation = False
                else:
                    asset.operation_name = None
                    asset.is_current_operation = False

        context['assets_by_area'] = {area_name: [asset for asset in assets if asset.area == area_code] for area_code, area_name in AREAS.items()}
        context['area_icons'] = {'a': 'fa-ship', 'c': 'fa-solid fa-ferry', 'o': 'fa-water', 'l': 'fa-building', 'v': 'fa-car', 'x': 'fa-cogs'}
        context['places'] = Place.objects.all()
        context['supervisors'] = User.objects.filter(groups__name__in=['maq_members', 'mto_members'])
        context['capitanes'] = User.objects.filter(groups__name='maq_members')
        return context
    
    def post(self, request, *args, **kwargs):
        asset_pk = request.POST.get('asset_pk')
        if not asset_pk:
            messages.error(request, "No se ha especificado el asset a actualizar.")
            return redirect('got:asset-list')

        asset = get_object_or_404(Asset, pk=asset_pk)
        action = request.POST.get('action')

        if action == 'update_place':
            place_id = request.POST.get('selected_place')
            if place_id:
                place = get_object_or_404(Place, pk=place_id)
                asset.place = place
                asset.save()
                messages.success(request, "La ubicación del asset se ha actualizado correctamente.")
            else:
                messages.error(request, "No se seleccionó ninguna ubicación.")

        elif action == 'update_supervisor':
            supervisor = asset.supervisor
            if supervisor.groups.filter(name__in=['maq_members', 'buzos_members']).exists():
                first_name = request.POST.get('first_name', '').strip()
                last_name = request.POST.get('last_name', '').strip()
                if not first_name or not last_name:
                    messages.error(request, "El nombre y el apellido del supervisor son requeridos.")
                    return redirect('got:asset-list')
                supervisor.first_name = first_name
                supervisor.last_name = last_name
                supervisor.save()
                messages.success(request, "Supervisor actualizado correctamente.")
            else:
                messages.error(request, "No se puede cambiar el nombre de este usuario.")
                return redirect('got:asset-list')

        elif action == 'update_capitan':
            capitan = asset.capitan
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            if not first_name or not last_name:
                messages.error(request, "El nombre y el apellido del capitán son requeridos.")
                return redirect('got:asset-list')
            capitan.first_name = first_name
            capitan.last_name = last_name
            capitan.save()
            messages.success(request, "Capitán actualizado correctamente.")
        else:
            messages.error(request, "Acción no reconocida.")
        return redirect('got:asset-list')
    

class AssetDetailView(LoginRequiredMixin, generic.DetailView):
    model = Asset
    template_name = 'got/assets/asset_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        asset = self.get_object()
        context['consumibles'] = Suministro.objects.filter(asset=asset).exists()
        context['items_by_subsystem'] = supplies_summary(asset)
        context['sys_form'] = SysForm()
        return context

    def post(self, request, *args, **kwargs):
        asset = self.get_object()

        if request.POST.get('action') == 'delete_system':
            sys_id = request.POST.get('sys_id')
            system = get_object_or_404(System, id=sys_id, asset=asset)
            system_name = system.name
            system.delete()
            messages.success(request, f'El sistema "{system_name}" ha sido eliminado correctamente.')
            return redirect(request.path)
        
        sys_form = SysForm(request.POST)
        if sys_form.is_valid():
            sys = sys_form.save(commit=False)
            sys.asset = asset
            sys.save()
            return redirect(request.path)

        context = self.get_context_data()
        context['sys_form'] = sys_form
        return render(request, self.template_name, context)