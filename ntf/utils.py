# ntf/utils.py (o en un archivo helper similar)
import json
import logging
import os
from pywebpush import webpush, WebPushException
from django.conf import settings

logger = logging.getLogger(__name__)

# Asegúrate de tener definidas en tu entorno las siguientes variables:
# VAPID_PRIVATE_KEY y VAPID_PUBLIC_KEY
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY")
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY")
VAPID_CLAIMS = {
    "sub": "mailto:analistamto@serport.co"  # Ajusta con tu correo
}

def send_push_notification(subscription, payload):
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh,
                    "auth": subscription.auth,
                },
            },
            data=json.dumps(payload),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=VAPID_CLAIMS,
        )
    except WebPushException as ex:
        logger.error("Error al enviar push notification: %s", repr(ex))
