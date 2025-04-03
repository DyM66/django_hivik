from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import generic
from django.urls import reverse

from got.models import System, Equipo, Ruta

'SYSTEMS VIEW'
class SysDetailView(LoginRequiredMixin, generic.DetailView):
    model = System
    template_name = "got/systems/system_base.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        system = self.get_object()

        next_url = self.request.GET.get('next')
        if not next_url:
            next_url = reverse('got:asset-detail', args=[system.asset.abbreviation])
        context['next_url'] = next_url

        main_equipos = Equipo.objects.filter(system=system, related__isnull=True)
        # Para cada equipo, obtenemos sus dependientes
        equipos_con_dependientes = []
        for eq in main_equipos:
            dependientes = eq.related_with.all()
            equipos_con_dependientes.append({'principal': eq, 'dependientes': dependientes,})
        context['equipos_con_dependientes'] = equipos_con_dependientes

        context['rutinas'] = Ruta.objects.filter(system=system).exclude(equipo__estado='f')
        return context