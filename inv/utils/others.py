# inv/utils.py
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def enviar_correo_transferencia(transferencia, equipo, sistema_origen, nuevo_sistema, observaciones):
    """
    Envía un correo de notificación de la transferencia de equipo, incluyendo:
      - Destinatarios fijos definidos en el código (o en settings).
      - Además, el correo del supervisor del asset del sistema de origen y del asset del sistema de destino.
    
    El contenido del correo se renderiza desde un template (transferencia.txt).
    """
    context = {
        'transferencia': transferencia,
        'equipo': equipo,
        'sistema_origen': sistema_origen,
        'nuevo_sistema': nuevo_sistema,
        'observaciones': observaciones,
        'equipos_relacionados': ", ".join([r.name for r in equipo.related_with.all()])
    }

    # Renderizamos el contenido del correo desde el template
    message = render_to_string('emails/transferencia.txt', context)
    
    # Asunto del correo, se podría obtener desde el template o definirlo aquí
    subject = f"Notificación de Transferencia de Equipo: {equipo.name}"
    
    # Destinatarios: define la lista de correos que deben recibir la notificación
    static_recipients = ['analistamto@serport.co', 'inventario@serport.co']

    # Destinatarios dinámicos: se extraen de los supervisores de los assets de los sistemas
    dynamic_recipients = []
    # Para el sistema de origen
    if sistema_origen.asset and sistema_origen.asset.supervisor and sistema_origen.asset.supervisor.email:
        dynamic_recipients.append(sistema_origen.asset.supervisor.email)
    # Para el sistema de destino
    if nuevo_sistema.asset and nuevo_sistema.asset.supervisor and nuevo_sistema.asset.supervisor.email:
        dynamic_recipients.append(nuevo_sistema.asset.supervisor.email)
    
    # Combinar ambas listas y eliminar duplicados
    all_recipients = list(set(static_recipients + dynamic_recipients))
    
    try:
        email = EmailMessage(subject, message, settings.EMAIL_HOST_USER, all_recipients)
        email.send()
    except Exception as e:
        logger.error(f"Error enviando correo de transferencia: {e}")