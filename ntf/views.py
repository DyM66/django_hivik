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
            data = json.loads(request.body)
            endpoint = data["endpoint"]
            keys = data["keys"]
            WebPushSubscription.objects.update_or_create(
                user=request.user,
                endpoint=endpoint,
                defaults={
                    "p256dh": keys["p256dh"],
                    "auth": keys["auth"]
                },
            )
            return JsonResponse({"success": True})
        except Exception as e:
            print("Error:", e)
            return JsonResponse({"success": False, "error": str(e)}, status=500)



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

