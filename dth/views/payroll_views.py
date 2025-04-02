# dth/views/payroll_views.py
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.views.generic import ListView, UpdateView, TemplateView
from django.views.decorators.http import require_GET, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse_lazy
from django.template.loader import render_to_string
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import date

from dth.models.payroll import Nomina, UserProfile
from dth.models.positions import Position, Document, PositionDocument, EmployeeDocument
from dth.forms import NominaForm, PositionForm, DocumentForm


class NominaListView(ListView):
    model = Nomina
    template_name = 'dth/payroll_views/payroll_list.html'
    context_object_name = 'nominas'
    paginate_by = 24
    ordering = ['surname', 'name', 'position_id__name']

    def get_queryset(self):
        qs = super().get_queryset()

        # 1. Filtro por texto (búsqueda en name o surname)
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

    # 1) Los docs requeridos para el cargo:
    pos_docs = PositionDocument.objects.filter(position=nomina.position_id).select_related('document').order_by('document__name')

    # 2) Tomar EmployeeDocument de este nomina, mapeado por document_id
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
            return render(request, 'dth/nomina_form.html', {'form': form})


class NominaUpdateView(UpdateView):
    model = Nomina
    form_class = NominaForm
    template_name = 'dth/payroll_views/payroll_update.html'
    success_url = reverse_lazy('dth:nomina_list')


@login_required
@require_http_methods(["GET", "POST"])
def edit_document(request, doc_id):
    """
    Edita un documento de la tabla Document. El botón de eliminar
    se invoca sólo dentro del modal edit-document, no en la tabla principal.
    """
    document = get_object_or_404(Document, pk=doc_id)

    if request.method == 'POST':
        form = DocumentForm(request.POST, instance=document)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Documento actualizado correctamente.'})
        else:
            html = render_to_string('dth/document_form_partial.html', {'form': form, 'document': document}, request=request)
            return JsonResponse({'success': False, 'html': html})
    else:
        # GET => retornar el formulario para editar
        form = DocumentForm(instance=document)
        html = render_to_string('dth/document_form_partial.html', {
            'form': form, 'document': document, 'is_editing': True
            }, request=request)
        return JsonResponse({'success': True, 'html': html})


@login_required
@require_http_methods(["POST"])
def delete_document(request, doc_id):
    """
    Elimina un documento. Se invoca al hacer clic en 'Eliminar'
    dentro del modal de edición de documento.
    """
    document = get_object_or_404(Document, pk=doc_id)
    document.delete()
    return JsonResponse({'success': True, 'message': 'Documento eliminado correctamente.'})




@login_required
@require_http_methods(["GET", "POST"])
def create_position(request):
    if request.method == 'POST':
        form = PositionForm(request.POST)
        if form.is_valid():
            position = form.save()
            return JsonResponse({'success': True, 'position_id': position.id, 'position_name': position.name})
        else:
            html = render_to_string('dth/payroll_views/position_form.html', {'form': form}, request=request)
            return JsonResponse({'success': False, 'html': html})
    else:
        form = PositionForm()
        html = render_to_string('dth/payroll_views/position_form.html', {'form': form}, request=request)
        return JsonResponse({'success': True, 'html': html})
    

@login_required
@require_http_methods(["GET", "POST"])
def edit_position(request, position_id):
    position = get_object_or_404(Position, pk=position_id)

    if request.method == 'POST':
        form = PositionForm(request.POST, instance=position)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True, 'message': 'Cargo actualizado correctamente.'})
        else:
            html = render_to_string('dth/payroll_views/position_form.html', {'form': form, 'position': position}, request=request)
            return JsonResponse({'success': False, 'html': html})
    else:
        form = PositionForm(instance=position)
        # Renderizamos un template parcial con el formulario
        position_form_html = render_to_string(
            'dth/payroll_views/position_form.html',
            {'form': form, 'position': position},
            request=request
        )

        associated_docs = position.position_documents.select_related('document').order_by('document__name')

        all_documents = Document.objects.all().order_by('name')
        associate_docs_html = render_to_string(
            'dth/payroll_views/position_docs_partial.html',
            {
                'position': position,
                'associated_docs': associated_docs,
                'documents': all_documents, 
            },
            request=request
        )

        combined_html = render_to_string(
            'dth/payroll_views/position_modal_content.html',
            {
                'position_form_html': position_form_html,
                'associate_docs_html': associate_docs_html,
                'position': position
            },
            request=request
        )
        return JsonResponse({'success': True, 'html': combined_html})


@login_required
@require_http_methods(["POST"])
@csrf_exempt  # si tuvieras problemas con CSRF, pero lo ideal es incluir CSRF en el POST
def delete_position(request, position_id):
    """
    Elimina un cargo (Position) por ID.
    """
    position = get_object_or_404(Position, pk=position_id)
    position.delete()
    return JsonResponse({'success': True, 'message': 'Cargo eliminado satisfactoriamente.'})


class PositionDocumentListView(LoginRequiredMixin, TemplateView):
    """
    Vista principal que lista:
    1) Grupos de Cargos (positions) con su respectiva tarjeta.
    2) Lista de Documentos en tabla, solo con botón Editar.
       Eliminar se hace dentro del modal.
    """
    template_name = 'dth/position_documents_list.html'

    def get_context_data(self, **kwargs):
        categories = [('o', 'Operativo'), ('a', 'Administrativo'), ('m', 'Mixto')]
        grouped_positions = []
        for code, category_name in categories:
            positions = Position.objects.filter(category=code).prefetch_related('position_documents__document').order_by('name')
            grouped_positions.append({
                'category': category_name,
                'positions': positions
            })

        documents = Document.objects.all().order_by('name')

        context = super().get_context_data(**kwargs)
        context['grouped_positions'] = grouped_positions
        context['documents'] = documents
        return context

    def get(self, request, *args, **kwargs):
        action = request.GET.get('action')
        doc_id = request.GET.get('id')

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if action == 'create_document':
                return JsonResponse({
                    'success': True,
                    'editing': False,
                    'doc_id': None,
                    'doc_name': '',
                    'doc_description': '',  # <---- añade aquí
                })
            elif action == 'edit_document' and doc_id:
                document = get_object_or_404(Document, id=doc_id)
                return JsonResponse({
                    'success': True,
                    'editing': True,
                    'doc_id': document.id,
                    'doc_name': document.name,
                    'doc_description': document.description or '',  # <---- añade aquí
                })

        return super().get(request, *args, **kwargs)



    def post(self, request, *args, **kwargs):
        """
        Maneja create_document / edit_document / delete_document
        NOTA: Para delete_document, redireccionamos al método delete_document
        en lugar de gestionarlo aquí, si quieres manejar todo aquí, se podría, pero
        ya tenemos la función delete_document aparte.
        """
        action = request.POST.get('action')
        doc_id = request.POST.get('id')

        if action == 'create_document':
            form = DocumentForm(request.POST)
        elif action == 'edit_document' and doc_id:
            document = get_object_or_404(Document, id=doc_id)
            form = DocumentForm(request.POST, instance=document)
        elif action == 'delete_document' and doc_id:
            return delete_document(request, doc_id)  # Usa la vista ya definida
        else:
            return JsonResponse({'success': False, 'message': 'Acción inválida.'})

        if form.is_valid():
            form.save()
            action_msg = 'creado' if action == 'create_document' else 'actualizado'
            return JsonResponse({'success': True, 'message': f'Documento {action_msg} correctamente.'})
        else:
            html = render_to_string('dth/document_form_partial.html', {'form': form}, request=request)
            return JsonResponse({'success': False, 'html': html, 'message': 'Por favor corrija los errores del formulario.'})


@login_required
@require_http_methods(["POST"])
def create_position_document(request):
    position_id = request.POST.get('position_id')
    document_id = request.POST.get('document_id')
    # Corregimos la forma en que leemos "mandatory"
    raw_val = request.POST.get('mandatory')
    # raw_val será "on" si la casilla está marcada (o "true" si pusiste value="true")
    if raw_val in ["on", "true"]:
        mandatory = True
    else:
        mandatory = False

    try:
        pd, created = PositionDocument.objects.get_or_create(
            position_id=position_id,
            document_id=document_id,
            defaults={'mandatory': mandatory}
        )
        if created:
            return JsonResponse({'success': True, 'message': 'Documento asociado correctamente.'})
        else:
            return JsonResponse({'success': False, 'message': 'Esta asociación ya existe.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})



@login_required
@require_http_methods(["POST"])
def delete_position_document(request):
    """
    Elimina la relación PositionDocument por ID (pd_id).
    """
    pd_id = request.POST.get('pd_id')
    pd = get_object_or_404(PositionDocument, id=pd_id)
    pd.delete()
    return JsonResponse({'success': True, 'message': 'Documento desasociado correctamente.'})


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
                return render(request, 'dth/nomina_form.html', {'form': form, 'object': nomina_obj})

    else:
        # GET => Muestra el formulario de edición
        form = NominaForm(instance=nomina_obj)

        # Si quieres devolver partial si es AJAX, podrías chequear:
        # if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        #     html = render_to_string('dth/partials/nomina_edit_form_partial.html',
        #                             {'form': form, 'nomina': nomina_obj},
        #                             request=request)
        #     return JsonResponse({'html': html})
        # else:

        # GET normal => Renderiza tu template habitual:
        return render(request, 'dth/nomina_form.html', {'form': form, 'object': nomina_obj})