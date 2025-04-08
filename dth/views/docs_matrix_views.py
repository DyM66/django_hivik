# dth/views/payroll_docs_views.py (ejemplo)
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from collections import defaultdict
from datetime import date

from dth.models.positions import Document, PositionDocument, EmployeeDocument
from dth.models.payroll import Nomina


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
    employees = list(Nomina.objects.select_related('position_id').filter(employment_status='a').order_by('surname', 'name'))
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
    return render(request, 'dth/docs_matrix_templates/nomina_documents_matrix.html', context)


# 3.1 GET => Form partial => se rellena con {employee_id, document_id}
@login_required
@require_http_methods(["GET"])
def upload_employee_document(request):
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
    html = render(request, 'dth/docs_matrix_templates/employee_document_form.html', context)
    return html


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

    return render(request, 'dth/docs_matrix_templates/employee_document_preview.html', {
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
