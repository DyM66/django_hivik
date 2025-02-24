# got/context_processors.py

from inv.models import Solicitud
from django.db.models import Q

def unapproved_requests_count(request):
    if request.user.is_authenticated:
        # Obtener las solicitudes no aprobadas que el usuario puede ver
        # Aquí debes aplicar la lógica de permisos adecuada
        solicitudes_no_aprobadas = Solicitud.objects.filter(
            approved=False,
            # Agrega filtros adicionales según tus necesidades de permisos
        )

        # Si tienes un sistema de permisos más complejo, ajusta el filtro
        # Por ejemplo, si solo quieres mostrar las solicitudes asignadas al usuario:
        # solicitudes_no_aprobadas = solicitudes_no_aprobadas.filter(responsable=request.user)

        count = solicitudes_no_aprobadas.count()
    else:
        count = 0

    return {'unapproved_requests_count': count}
