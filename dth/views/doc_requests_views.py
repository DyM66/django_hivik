# dth/views/docs_requests_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.contrib import messages

from dth.models.payroll import Nomina
from dth.models.docs_requests import DocumentRequest, DocumentRequestItem
from dth.models.positions import EmployeeDocument, Document
from dth.utils.documents_helpers import get_documents_states_for_employee

import uuid


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
                return render(request, 'dth/docs_requests_templates/public_docs_request/login_pin.html', context)
        else:
            # GET => mostrar form cédula
            return render(request, 'dth/docs_requests_templates/public_docs_request/login_pin.html')

    # 2. Si todos los documentos han sido aprobados, se cierra el proceso.
    all_approved = all(item.status == DocumentRequestItem.STATUS_APPROVED for item in doc_request.items.all())
    if all_approved:
        return render(request, 'dth/invalid_request.html', status=404)

    # 3. Verificar si se han subido todos los documentos (que tengan archivo asociado)
    all_uploaded = all(item.pdf_file for item in doc_request.items.all())
    if all_uploaded:
        return render(request, 'dth/docs_requests_templates/public_docs_request/upload_success.html', {'doc_request': doc_request})


    # 4. Caso normal: mostrar el formulario para subir o re-subir los documentos.
    return render(request, 'dth/docs_requests_templates/public_docs_request/upload_form.html', {
        'doc_request': doc_request,
        'items': doc_request.items.all()
    })

    # Fase 2: Ya validamos la cédula, mostramos la página de subida
    # items = doc_request.items.select_related('document').all()

    # if request.method == 'POST':
    #     # Guardar los archivos subidos
    #     for item in items:
    #         file_field_name = f"file_{item.id}"
    #         expiration_field_name = f"expiration_{item.id}"
    #         f = request.FILES.get(file_field_name, None)
    #         exp = request.POST.get(expiration_field_name, '').strip()

    #         if f:
    #             item.pdf_file = f
    #         if exp:
    #             item.expiration_date = exp
    #         item.save()
    #     return redirect('dth:document_upload_view', token=token)

    # context = {
    #     'doc_request': doc_request,
    #     'items': items
    # }
    # return render(request, 'dth/docs_requests_templates/public_docs_request/upload_form.html', context)


@login_required
def request_docs_form(request, emp_id):
    """
    Muestra un formulario con los documentos requeridos (Pendiente/Vencido),
    y un botón "Solicitar". Sin usar AJAX.
    """
    employee = get_object_or_404(Nomina, pk=emp_id)
    doc_states = get_documents_states_for_employee(employee, only_required=True)

    return render(request, 'dth/docs_requests_templates/request_docs_form.html', {
        'employee': employee,
        'doc_states': doc_states,
    })


@login_required
def request_docs_submit(request):
    if request.method != 'POST':
        return HttpResponse("Método no permitido.", status=405)
    
    employee_id = request.POST.get('employee_id')
    documents_selected = request.POST.getlist('documents')  # la lista de IDs
    email = request.POST.get('email', '').strip()
    employee = get_object_or_404(Nomina, pk=employee_id)

    # 1. Validar que se haya ingresado correo y que se hayan seleccionado documentos
    if not email:
        return render(request, 'dth/docs_requests_templates/request_docs_error.html', {
            'message': 'Debe proporcionar un correo electrónico.'
        })

    if not documents_selected:
        return render(request, 'dth/docs_requests_templates/request_docs_error.html', {
            'message': 'No se seleccionó ningún documento.'
        })

    employee.email = email
    employee.save()

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

    upload_link = request.build_absolute_uri(
        reverse('dth:document_upload_view', kwargs={'token': token})
    )
    
    subject = "Solicitud de Documentos - SERPORT"
    # Puedes usar render_to_string con una plantilla HTML para el cuerpo del email
    html_message = render_to_string('dth/docs_requests_templates/email_request_documents.html', {
        'employee': employee,
        'upload_link': upload_link,
        'doc_req': doc_req,
    })

    # send_mail retorna el número de emails enviados
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@serport.com')
    recipient_list = [employee.email]
    send_mail(
        subject,
        # Mensaje de texto plano (por si el cliente de correo no soporta HTML)
        f"Hola {employee.name}, por favor ingresa al siguiente enlace para cargar tus documentos: {upload_link}",
        from_email,
        recipient_list,
        fail_silently=False,
        html_message=html_message  # cuerpo en HTML
    )


    messages.success(request, f"Se ha enviado el correo de solicitud de documentos a {employee.email}.")
    return redirect('dth:nomina_documents_matrix')  # ajusta el nombre del url pattern a tu preferencia


@login_required
def admin_document_request_list(request):
    """
    Lista todas las solicitudes de documentos (DocumentRequest).
    """
    requests = DocumentRequest.objects.select_related('employee').order_by('-created_at')
    return render(request, 'dth/docs_requests_templates/list.html', {
        'requests': requests
    })


@login_required
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
        item.status = DocumentRequestItem.STATUS_APPROVED
        item.verified_by = request.user
        item.approved_at = timezone.now()
        item.rejection_reason = ""
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

        return JsonResponse({
            "success": True,
            "message": "Documento aprobado y guardado en la ficha del empleado.",
        })

    return render(request, 'dth/docs_requests_templates/detail.html', {
        'doc_req': doc_req,
        'items': items
    })

@login_required(False)  # o sin login_required si es pública
def document_upload_success(request):
    """
    Página de confirmación de que los documentos se han cargado.
    """
    return render(request, 'dth/docs_requests_templates/public_docs_request/upload_success.html')



@require_http_methods(["POST"])
def document_upload_partial(request):
    """
    Recibe item_id, file, expiration_date, etc. en POST/FILES 
    y guarda la info de DocumentRequestItem.
    Retorna JSON con success/error.
    """
    item_id = request.POST.get('item_id', None)
    if not item_id:
        return JsonResponse({"success": False, "error": "Falta item_id"}, status=400)

    doc_item = get_object_or_404(DocumentRequestItem, pk=item_id)

    # Revisa si vino el archivo
    file = request.FILES.get('file', None)
    if not file:
        return JsonResponse({"success": False, "error": "No se recibió el archivo"}, status=400)

    # Validar extensión PDF
    if not file.name.lower().endswith('.pdf'):
        return JsonResponse({"success": False, "error": "Debe ser un archivo PDF."}, status=400)
    
    # Guardar archivo en doc_item
    doc_item.pdf_file = file

    # Manejar fecha de expiración
    expiration_date = request.POST.get('expiration_date', '')
    if expiration_date:
        doc_item.expiration_date = expiration_date

    doc_item.save()

    return JsonResponse({"success": True})


@require_POST
def reject_document_request_item(request):
    try:
        item_id = request.POST.get('item_id')
        rejected_reason = request.POST.get('rejected_reason', '').strip()
        if not item_id or not rejected_reason:
            return JsonResponse({"success": False, "error": "Faltan datos requeridos."}, status=400)

        item = get_object_or_404(DocumentRequestItem, pk=item_id)

        # Marcar el item como rechazado y guardar la justificación
        item.status = DocumentRequestItem.STATUS_REJECTED
        item.rejection_reason = rejected_reason
        # Borrar el archivo para forzar la re-subida, si existe
        item.pdf_file = None
        item.save()

        # Enviar correo de notificación al empleado
        upload_link = request.build_absolute_uri(
            reverse('dth:document_upload_view', kwargs={'token': item.request.token})
        )
        subject = "Documento Rechazado - SERPORT"
        html_message = render_to_string('dth/docs_requests_templates/email_rejected_document.html', {
            'employee': item.request.employee,
            'upload_link': upload_link,
            'document': item.document,
            'rejected_reason': rejected_reason,
        })
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@serport.com')
        recipient_list = [item.request.employee.email]
        send_mail(
            subject,
            f"El documento {item.document.name} fue rechazado. Motivo: {rejected_reason}. Ingresa al siguiente enlace para re-subirlo: {upload_link}",
            from_email,
            recipient_list,
            html_message=html_message,
            fail_silently=False
        )

        return JsonResponse({"success": True, "message": "Documento rechazado exitosamente."})
    except Exception as e:
        # Imprime el traceback en consola para depuración
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "error": str(e)}, status=500)

