from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt

from dth.models.positions import Document, Position, PositionDocument
from dth.forms import DocumentForm, PositionForm

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
            html = render_to_string('dth/job_profile_templetes/document_form_partial.html', {'form': form, 'document': document}, request=request)
            return JsonResponse({'success': False, 'html': html})
    else:
        # GET => retornar el formulario para editar
        form = DocumentForm(instance=document)
        html = render_to_string('dth/job_profile_templetes/document_form_partial.html', {
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
            html = render_to_string('dth/job_profile_templetes/position_form.html', {'form': form}, request=request)
            return JsonResponse({'success': False, 'html': html})
    else:
        form = PositionForm()
        html = render_to_string('dth/job_profile_templetes/position_form.html', {'form': form}, request=request)
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
            html = render_to_string('dth/job_profile_templetes/position_form.html', {'form': form, 'position': position}, request=request)
            return JsonResponse({'success': False, 'html': html})
    else:
        form = PositionForm(instance=position)
        # Renderizamos un template parcial con el formulario
        position_form_html = render_to_string(
            'dth/job_profile_templetes/position_form.html',
            {'form': form, 'position': position},
            request=request
        )

        associated_docs = position.position_documents.select_related('document').order_by('document__name')
        all_documents = Document.objects.all().order_by('name')
        associate_docs_html = render_to_string(
            'dth/job_profile_templetes/position_docs_partial.html',
            {
                'position': position,
                'associated_docs': associated_docs,
                'documents': all_documents, 
            },
            request=request
        )

        combined_html = render_to_string(
            'dth/job_profile_templetes/position_modal_content.html',
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
@csrf_exempt
def delete_position(request, position_id):
    """
    Elimina un cargo (Position) por ID.
    """
    position = get_object_or_404(Position, pk=position_id)
    position.delete()
    return JsonResponse({'success': True, 'message': 'Cargo eliminado satisfactoriamente.'})


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


class JobProfileListView(LoginRequiredMixin, TemplateView):
    """
    Vista principal que lista:
    1) Grupos de Cargos (positions) con su respectiva tarjeta.
    2) Lista de Documentos en tabla, solo con botón Editar.
       Eliminar se hace dentro del modal.
    """
    template_name = 'dth/job_profile_templates/position_documents_list.html'

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