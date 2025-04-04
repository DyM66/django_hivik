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