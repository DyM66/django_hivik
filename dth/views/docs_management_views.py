# dth/views/payroll_docs_views.py (ejemplo)
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from collections import defaultdict
from datetime import date
from django.template.loader import render_to_string
from django.utils import timezone

from dth.models.positions import Document, PositionDocument, EmployeeDocument
from dth.models.payroll import Nomina
from dth.models.docs_requests import DocumentRequest, DocumentRequestItem

@login_required
def nomina_documents_matrix(request):
    """
    Genera la "matriz" de documentos vs. empleados:
    - Filas => empleados (Nomina)
    - Columnas => documentos (Document)
    - Cada celda => estado (N/A, Pendiente, Vencido, Ok, Ok(x días)).
    """

    # 1) Traer todos los documentos (encabezados de columna)
    docs = list(Document.objects.all().order_by('name'))
    if not docs:
        # Si no hay documentos, la tabla tendrá solo 3 columnas base
        # Podrías meter un mensaje en el contexto
        pass

    # 2) Traer todos los empleados (Nomina) => filas
    employees = list(Nomina.objects.select_related('position_id').all().order_by('name', 'surname'))
    if not employees:
        # Si no hay empleados, la tabla no tendrá filas
        pass

    # 3) Cargar PositionDocument => saber si (position, doc) existe y si es mandatorio
    posdocs_qs = PositionDocument.objects.values('position_id', 'document_id', 'mandatory')
    posdoc_map = {}
    for pd in posdocs_qs:
        posdoc_map[(pd['position_id'], pd['document_id'])] = pd['mandatory']

    # 4) Cargar EmployeeDocument => para verificar expiración
    empdocs_qs = EmployeeDocument.objects.values('employee_id', 'document_id', 'expiration_date')
    empdoc_map = defaultdict(list)
    for ed in empdocs_qs:
        key = (ed['employee_id'], ed['document_id'])
        empdoc_map[key].append(ed['expiration_date'])

    # 5) Armar las filas => cada employee => row.cells => cada doc => estado
    rows = []
    today = date.today()

    for e in employees:
        row_data = {
            'employee': e,
            'cells': []
        }
        for d in docs:
            key_pd = (e.position_id_id, d.id)
            if key_pd not in posdoc_map:
                # => "N/A"
                row_data['cells'].append({
                    'state': "N/A",
                    'highlight': False,
                    'is_ok': False
                })
                continue

            # El cargo del empleado sí requiere ese doc
            is_mandatory = posdoc_map[key_pd]
            key_ed = (e.id, d.id)

            if key_ed not in empdoc_map:
                # => Pendiente
                row_data['cells'].append({
                    'state': "Pendiente",
                    'highlight': is_mandatory,  # Si es mandatorio => resaltar
                    'is_ok': False,
                    'employee_id': e.id,
                    'document_id': d.id
                })
            else:
                # => Tiene uno o varios EmployeeDocument => validar vencimientos
                expiration_list = empdoc_map[key_ed]  # [date1, date2, None...]
                any_valid = False
                closest_days_left = None

                for exp in expiration_list:
                    if exp is None:
                        # => sin fecha => no vence => OK
                        any_valid = True
                        closest_days_left = None
                        break
                    else:
                        if exp >= today:
                            # => hay un doc no vencido => OK
                            any_valid = True
                            days_left = (exp - today).days
                            # Tomamos el más próximo a vencer
                            if closest_days_left is None or days_left < closest_days_left:
                                closest_days_left = days_left

                if not any_valid:
                    # => todos vencidos
                    row_data['cells'].append({
                        'state': "Vencido",
                        'highlight': True,
                        'is_ok': False,
                        'employee_id': e.id,
                        'document_id': d.id
                    })
                else:
                    # => Ok
                    if closest_days_left is None:
                        st = "Ok"
                    else:
                        st = f"Ok ({closest_days_left} días)"
                    row_data['cells'].append({
                        'state': st,
                        'highlight': False,
                        'is_ok': True,
                        'employee_id': e.id,
                        'document_id': d.id
                    })
        rows.append(row_data)

    context = {
        'docs': docs,  # Columnas
        'rows': rows,  # Filas + celdas
    }
    return render(request, 'dth/nomina_documents_matrix.html', context)


# 3.1 GET => Form partial => se rellena con {employee_id, document_id}
@login_required
@require_http_methods(["GET"])
def employee_document_form(request):
    """
    Devuelve un partial HTML con el form para subir un doc
    Recibe ?emp=<id>&doc=<id>
    """
    employee_id = request.GET.get('emp')
    document_id = request.GET.get('doc')
    # Podrías validar existence
    context = {
        'employee_id': employee_id,
        'document_id': document_id,
    }
    html = render(request, 'dth/partials/employee_document_form.html', context)
    return html


# 3.2 POST => crear EmployeeDocument
@login_required
@require_http_methods(["POST"])
def create_employee_document(request):
    """
    Crea un EmployeeDocument con (employee_id, document_id, file, expiration_date).
    Retorna JSON {success:true} o {success:false,...}
    """
    employee_id = request.POST.get('employee_id')
    document_id = request.POST.get('document_id')
    file = request.FILES.get('file')  # <input type="file" name="file">
    expiration_date = request.POST.get('expiration_date') or None

    print(employee_id)
    print(document_id)
    print(file)
    print(expiration_date)

    # Validar
    if not employee_id or not document_id or not file:
        return JsonResponse({'success': False, 'message': 'Faltan datos.'})

    # Buscar
    employee = get_object_or_404(Nomina, pk=employee_id)
    doc = get_object_or_404(Document, pk=document_id)

    ed = EmployeeDocument.objects.create(
        employee=employee,
        document=doc,
        file=file
    )
    if expiration_date:
        ed.expiration_date = expiration_date
    ed.save()

    return JsonResponse({'success': True})


# 3.3 GET => "preview" partial => listar EmployeeDocument
@login_required
@require_http_methods(["GET"])
def employee_document_preview(request):
    """
    Muestra un partial con la lista de documentos subidos (EmployeeDocument)
    para un (employee, doc).
    """
    emp_id = request.GET.get('emp')
    doc_id = request.GET.get('doc')
    employee = get_object_or_404(Nomina, pk=emp_id)
    document = get_object_or_404(Document, pk=doc_id)
    documents = EmployeeDocument.objects.filter(employee=employee, document=document)

    return render(request, 'dth/partials/employee_document_preview.html', {
        'documents': documents
    })


# 3.4 POST => Eliminar un EmployeeDocument por id
@login_required
@require_http_methods(["POST"])
def delete_employee_document(request):
    """
    Elimina un EmployeeDocument por su id.
    """
    ed_id = request.POST.get('employee_doc_id')
    ed = get_object_or_404(EmployeeDocument, pk=ed_id)
    ed.delete()
    return JsonResponse({'success': True, 'message': 'Documento eliminado.'})

# dth/utils/documents_helpers.py

from collections import defaultdict
from datetime import date
from dth.models.positions import PositionDocument, EmployeeDocument, Document

def get_documents_states_for_employee(employee, only_required=True):
    """
    Retorna una lista de diccionarios con la forma:
    [
      {
        'document': <Document>,
        'state': 'Pendiente' | 'Vencido' | 'Ok'
      },
      ...
    ]

    - Si `only_required=True`, sólo incluye documentos que el cargo del empleado
      requiere (según PositionDocument).
    - Si no tiene ningún EmployeeDocument => 'Pendiente'
    - Si todos los ED que tiene están vencidos => 'Vencido'
    - Si al menos uno no está vencido => 'Ok'
    """

    position = employee.position_id
    # position podría ser None si no está asignado, verifica
    if not position:
        return []

    # 1) Tomar todos los Document requeridos para ese cargo (si only_required=True),
    #    de lo contrario, docs = Document.objects.all() 
    if only_required:
        required_doc_ids = PositionDocument.objects.filter(position=position).values_list('document_id', flat=True)
        docs = Document.objects.filter(pk__in=required_doc_ids).order_by('name')
    else:
        # si quisieras mostrar todos
        docs = Document.objects.all().order_by('name')

    # 2) Mapeo de doc => mandatory (si lo necesitaras)
    posdocs_qs = PositionDocument.objects.filter(position=position).values('document_id', 'mandatory')
    posdoc_map = {pd['document_id']: pd['mandatory'] for pd in posdocs_qs}

    # 3) Obtener todos los EmployeeDocument de este empleado
    empdocs_qs = EmployeeDocument.objects.filter(employee=employee).values('document_id', 'expiration_date')
    empdoc_map = defaultdict(list)
    for ed in empdocs_qs:
        empdoc_map[ed['document_id']].append(ed['expiration_date'])

    # 4) Revisamos cada doc y definimos el estado
    results = []
    today = date.today()

    for doc in docs:
        doc_id = doc.id
        if doc_id not in empdoc_map:
            # => no tiene nada => Pendiente
            results.append({
                'document': doc,
                'state': 'Pendiente'
            })
        else:
            # => Tiene uno o varios ED => verificar vencimientos
            expiration_list = empdoc_map[doc_id]
            all_expired = True
            for exp in expiration_list:
                if exp is None or exp >= today:
                    # => existe uno no vencido => Ok
                    all_expired = False
                    break
            if all_expired:
                state = 'Vencido'
            else:
                state = 'Ok'
            results.append({
                'document': doc,
                'state': state
            })

    return results



@login_required
@require_http_methods(["GET"])
def ajax_request_docs_modal(request):
    """
    Devuelve el HTML parcial con la lista de documentos del empleado,
    indicando cuáles están Pendiente/Vencido/Ok 
    (SOLO los requeridos para el cargo).
    """
    employee_id = request.GET.get('employee_id')
    employee = get_object_or_404(Nomina, pk=employee_id)

    # Usamos only_required=True
    doc_states = get_documents_states_for_employee(employee, only_required=True)

    context = {
        'employee': employee,
        'doc_states': doc_states,
    }
    html_form = render_to_string('dth/partials/request_docs_modal_form.html', context, request=request)
    return JsonResponse({'html': html_form})

@login_required
@require_http_methods(["POST"])
def create_document_request(request):
    """
    Recibe el POST con employee_id y la lista de documents[] seleccionados.
    Crea DocumentRequest y sus DocumentRequestItems.
    """
    print("== create_document_request was called ==")  # <--- log en consola
    employee_id = request.POST.get('employee_id')
    documents_selected = request.POST.getlist('documents')  # lista de IDs de Document

    print("employee_id =>", employee_id)
    print("documents_selected =>", documents_selected)

    employee = get_object_or_404(Nomina, pk=employee_id)

    if not documents_selected:
        return JsonResponse({'success': False, 'message': 'No se seleccionó ningún documento.'})

    import uuid
    token = uuid.uuid4().hex[:8]  # algo corto
    doc_req = DocumentRequest.objects.create(
        employee=employee,
        token=token
    )

    for doc_id in documents_selected:
        doc_obj = get_object_or_404(Document, pk=doc_id)
        DocumentRequestItem.objects.create(
            request=doc_req,
            document=doc_obj
        )

    link = f"https://localhost:8000/dth/document-upload/{token}"
    print("==== LINK ÚNICO PARA SOLICITUD: ====", link)

    return JsonResponse({'success': True, 'link': link})



@require_http_methods(["GET", "POST"])
def document_upload_view(request, token):
    """
    Vista pública (no requiere @login_required).
    1) Muestra un form con input para la cédula (si no está “autorizado”).
    2) Si se valida la cédula => muestra la lista de DocumentRequestItem
       donde podrá subir pdf + fecha expiración.
    3) Guarda los archivos en la tabla DocumentRequestItem.
    """
    try:
        doc_request = DocumentRequest.objects.select_related('employee').get(token=token)
    except DocumentRequest.DoesNotExist:
        return render(request, 'dth/invalid_request.html', status=404)

    # Fase 1: Si no se ha validado la cédula, pedimos un "PIN"
    if 'cedula_validada' not in request.session or request.session.get('cedula_validada') != doc_request.employee.id_number:
        if request.method == 'POST':
            entered_id = request.POST.get('id_number')
            if entered_id and entered_id.strip() == doc_request.employee.id_number.strip():
                # ok, cédula coincide
                request.session['cedula_validada'] = doc_request.employee.id_number
                return redirect('dth:document_upload_view', token=token)
            else:
                context = {
                    'error': "La cédula no coincide. Intente de nuevo."
                }
                return render(request, 'dth/public_docs_request/login_pin.html', context)
        else:
            # GET => mostrar form cédula
            return render(request, 'dth/public_docs_request/login_pin.html')

    # Fase 2: Ya validamos la cédula, mostramos la página de subida
    items = doc_request.items.select_related('document').all()

    if request.method == 'POST':
        # Guardar los archivos subidos
        for item in items:
            file_field_name = f"file_{item.id}"
            expiration_field_name = f"expiration_{item.id}"
            f = request.FILES.get(file_field_name, None)
            exp = request.POST.get(expiration_field_name, '').strip()

            if f:
                item.pdf_file = f
            if exp:
                item.expiration_date = exp
            item.save()
        return redirect('dth:document_upload_view', token=token)

    context = {
        'doc_request': doc_request,
        'items': items
    }
    return render(request, 'dth/public_docs_request/upload_form.html', context)



def is_dth_member(user):
    # Lógica para ver si el user pertenece al grupo/rol DTH
    return user.groups.filter(name='dth_members').exists()

@login_required
@user_passes_test(is_dth_member)
def admin_document_request_list(request):
    """
    Lista todas las solicitudes de documentos (DocumentRequest).
    """
    requests = DocumentRequest.objects.select_related('employee').order_by('-created_at')
    return render(request, 'dth/admin_docs_requests/list.html', {
        'requests': requests
    })

@login_required
@user_passes_test(is_dth_member)
def admin_document_request_detail(request, pk):
    """
    Muestra los items de una solicitud y permite aprobarlos.
    pk => DocumentRequest.id
    """
    doc_req = get_object_or_404(DocumentRequest, pk=pk)
    items = doc_req.items.select_related('document').all()

    if request.method == 'POST':
        # Aprobar un item en específico
        item_id = request.POST.get('item_id')
        item = get_object_or_404(DocumentRequestItem, id=item_id, request=doc_req)

        # Creamos EmployeeDocument en base a la info
        if not item.pdf_file:
            return JsonResponse({'success': False, 'message': 'No hay archivo para este documento.'})

        # Se aprueba
        item.approved = True
        item.verified_by = request.user
        item.approved_at = timezone.now()
        item.save()

        # Crea el EmployeeDocument
        # Reutiliza la url, no hace falta "mover" a otra carpeta si usas S3
        emp_doc = EmployeeDocument.objects.create(
            employee=doc_req.employee,
            document=item.document,
            file=item.pdf_file,
            expiration_date=item.expiration_date
        )
        emp_doc.save()

        return JsonResponse({'success': True, 'message': 'Documento aprobado y guardado en la ficha del empleado.'})

    return render(request, 'dth/admin_docs_requests/detail.html', {
        'doc_req': doc_req,
        'items': items
    })


# dth/views/docs_request_nonajax_view.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from dth.models.payroll import Nomina
from dth.models.positions import Document
from dth.models.docs_requests import DocumentRequest, DocumentRequestItem
import uuid

@login_required
def request_docs_form(request, emp_id):
    """
    Muestra un formulario con los documentos requeridos (Pendiente/Vencido),
    y un botón "Solicitar". Sin usar AJAX.
    """
    employee = get_object_or_404(Nomina, pk=emp_id)
    doc_states = get_documents_states_for_employee(employee, only_required=True)

    return render(request, 'dth/no_ajax/request_docs_form.html', {
        'employee': employee,
        'doc_states': doc_states,
    })


@login_required
def request_docs_submit(request):
    """
    Procesa el form (POST) con employee_id y checkboxes (documents[]).
    Crea DocumentRequest y sus items, y redirige a una página de confirmación.
    """
    if request.method != 'POST':
        return HttpResponse("Método no permitido.", status=405)
    
    employee_id = request.POST.get('employee_id')
    documents_selected = request.POST.getlist('documents')  # la lista de IDs
    employee = get_object_or_404(Nomina, pk=employee_id)

    if not documents_selected:
        return render(request, 'dth/no_ajax/request_docs_error.html', {
            'message': 'No se seleccionó ningún documento.'
        })

    token = uuid.uuid4().hex[:8]
    doc_req = DocumentRequest.objects.create(
        employee=employee,
        token=token
    )

    for doc_id in documents_selected:
        doc_obj = get_object_or_404(Document, pk=doc_id)
        DocumentRequestItem.objects.create(
            request=doc_req,
            document=doc_obj
        )
    
    link = f"http://localhost:8000/dth/document-upload/{token}"
    return render(request, 'dth/no_ajax/request_docs_success.html', {
        'link': link,
        'employee': employee,
    })
