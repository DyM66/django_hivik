import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import WebPushSubscription

@login_required
@csrf_exempt
def save_push_subscription(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode('utf-8'))
            endpoint = data.get("endpoint")
            keys = data.get("keys", {})
            p256dh = keys.get("p256dh")
            auth_key = keys.get("auth")
            if not endpoint or not p256dh or not auth_key:
                return JsonResponse({"error": "Datos incompletos"}, status=400)
            # Actualiza o crea la suscripción para el usuario
            subscription, created = WebPushSubscription.objects.update_or_create(
                user=request.user,
                endpoint=endpoint,
                defaults={"p256dh": p256dh, "auth": auth_key},
            )
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Método no permitido"}, status=405)


from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Notification, WebPushSubscription
from .utils import send_push_notification
from django.utils import timezone

@login_required
def test_push_notification(request):
    user = request.user
    notification = Notification.objects.create(
        user=user,
        title="Notificación de prueba",
        message=f"Esta es una notificación push generada el {timezone.now().strftime('%d/%m/%Y %H:%M:%S')}",
        redirect_url="/got/"  # Ajusta a la URL que desees
    )

    payload = {
        "title": notification.title,
        "message": notification.message,
        "redirect_url": notification.redirect_url,
        "created_at": notification.created_at.strftime("%d/%m/%Y %H:%M")
    }

    subscriptions = user.push_subscriptions.all()
    for sub in subscriptions:
        send_push_notification(sub, payload)

    return JsonResponse({"success": True, "message": "Notificación enviada con éxito"})

