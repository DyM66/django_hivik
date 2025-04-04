# dth/views/payroll_views.py
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.views.generic import ListView, UpdateView
from django.views.decorators.http import require_GET, require_http_methods
from django.urls import reverse_lazy
from django.template.loader import render_to_string
from datetime import date

from dth.models.payroll import Nomina, UserProfile
from dth.models.positions import Position, PositionDocument, EmployeeDocument
from dth.forms import NominaForm


class NominaListView(ListView):
    model = Nomina
    template_name = 'dth/payroll_views/payroll_list.html'
    context_object_name = 'nominas'
    paginate_by = 24
    ordering = ['surname', 'name', 'position_id__name']

    def get_queryset(self):
        qs = super().get_queryset()
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            qs = qs.filter(models.Q(name__icontains=search_query) | models.Q(surname__icontains=search_query))

        # 2. Filtro por cargos (positions)
        selected_positions = self.request.GET.getlist('positions', [])
        # Si se incluyó "all", ignoramos el resto
        if 'all' in selected_positions:
            selected_positions = []

        if selected_positions:
            # Filtra por la FK (position_id) en la lista de IDs
            qs = qs.filter(position_id__in=selected_positions)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_positions = Position.objects.all().order_by('name')
        context['positions'] = all_positions
        context['selected_positions'] = self.request.GET.getlist('positions', [])
        context['search_query'] = self.request.GET.get('search', '')
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        context['view_mode'] = profile.payroll_view_mode 
        return context


@require_GET
def nomina_detail_partial(request, pk):
    nomina = get_object_or_404(Nomina, pk=pk)
    today = date.today()
    pos_docs = PositionDocument.objects.filter(position=nomina.position_id).select_related('document').order_by('document__name')
    emp_docs = EmployeeDocument.objects.filter(employee=nomina)
    doc_map = {}  # doc_id -> lista de (expiration_date, file)
    for ed in emp_docs:
        doc_id = ed.document_id
        if doc_id not in doc_map:
            doc_map[doc_id] = []
        doc_map[doc_id].append({'expiration_date': ed.expiration_date, 'file': ed.file.url if ed.file else None,})

    # 3) Construir la listita de estado
    doc_status_list = []
    for pd in pos_docs:
        d = pd.document
        doc_id = d.id

        # Ver si existe en doc_map
        if doc_id not in doc_map:
            # => Pendiente
            doc_status_list.append({
                'document_name': d.name,
                'state': 'Pendiente',
                'file_url': None,
                'expired': False,
            })
            continue

        found_ok = False
        found_file_url = None
        all_vencidos = True

        # si uno no venció => state=Ok
        for data in doc_map[doc_id]:
            exp = data['expiration_date']
            file_url = data['file']
            if exp is None or exp >= today:
                # => no vencido => Ok
                found_ok = True
                found_file_url = file_url
                all_vencidos = False
                break
        if found_ok:
            doc_status_list.append({
                'document_name': d.name,
                'state': 'Ok',
                'file_url': found_file_url,
                'expired': False,
            })
        else:
            # => todos vencidos
            doc_status_list.append({
                'document_name': d.name,
                'state': 'Vencido',
                'file_url': doc_map[doc_id][0]['file'],  # cualquiera
                'expired': True,
            })

    # Renderizamos
    html = render_to_string(
        'dth/payroll_views/payroll_detail.html',
        {
            'nomina': nomina,
            'doc_status_list': doc_status_list
        },
        request=request
    )
    return HttpResponse(html, content_type='text/html')


@login_required
def nomina_create(request):
    """
    Crea un nuevo registro de Nomina.
    Si es GET normal => render normal
    Si es GET Ajax => devolver partial
    Si es POST => crear y responder JSON
    """
    if request.method == 'POST':
        form = NominaForm(request.POST)
        if form.is_valid():
            obj = form.save()
            return JsonResponse({'success': True, 'pk': obj.pk})
        else:
            # Devolver HTML con errores
            html = render_to_string('dth/payroll_views/nomina_form_partial.html', {'form': form}, request=request)
            return JsonResponse({'success': False, 'html': html})
    else:
        # GET
        form = NominaForm()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Devolvemos partial
            html = render_to_string('dth/payroll_views/nomina_form_partial.html', {'form': form}, request=request)
            return JsonResponse({'success': True, 'html': html})
        else:
            # GET normal => la antigua vista con redirect
            return render(request, 'dth/payroll_views/nomina_form.html', {'form': form})


class NominaUpdateView(UpdateView):
    model = Nomina
    form_class = NominaForm
    template_name = 'dth/payroll_views/payroll_update.html'
    success_url = reverse_lazy('dth:nomina_list')


@login_required
@require_http_methods(["GET", "POST"])
def nomina_edit(request, pk):
    """
    Vista para editar o eliminar un registro de Nomina:
    - GET: Muestra el formulario de edición (si no es AJAX) o un partial (si quisieras).
    - POST con 'action=delete': Elimina el registro.
        * Si AJAX => JSON {'deleted': True}
        * Si no es AJAX => redirige con mensaje.
    - POST normal => intenta actualizar (edición) con NominaForm.
        * Si válido => guarda y redirige (o podrías devolver JSON si es AJAX).
    """
    nomina_obj = get_object_or_404(Nomina, pk=pk)

    if request.method == 'POST':
        # 1) Checar si es petición de borrado:
        action = request.POST.get('action')
        if action == 'delete':
            # Eliminar el registro
            nomina_obj.delete()

            # Si es AJAX => devolver JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'deleted': True})
            else:
                # No es AJAX => redirigir con mensaje
                messages.success(request, "Empleado eliminado con éxito.")
                return redirect('dth:nomina_list')  # Ajusta la ruta o el name de la URL

        # 2) De lo contrario, es edición:
        form = NominaForm(request.POST, instance=nomina_obj)
        if form.is_valid():
            form.save()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Registro actualizado'})
            else:
                messages.success(request, "Registro de nómina actualizado.")
                return redirect('dth:nomina_list')  # Ajusta a donde quieras redirigir
        else:
            # Form inválido
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Podrías devolver partial con el form y errores
                return JsonResponse({'success': False, 'errors': form.errors})
            else:
                messages.error(request, "Por favor revisa los campos del formulario.")
                # Renderiza el template de edición con errores
                return render(request, 'dth/payroll_views/nomina_form.html', {'form': form, 'object': nomina_obj})

    else:
        # GET => Muestra el formulario de edición
        form = NominaForm(instance=nomina_obj)
        return render(request, 'dth/payroll_views/nomina_form.html', {'form': form, 'object': nomina_obj})