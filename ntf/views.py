from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from ntf.models import Notification


@login_required
def get_notifications(request):
    try:
        user = request.user
        notifications = user.notifications.filter(seen=False)
        data = [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "redirect_url": n.redirect_url,
                "created_at": n.created_at.strftime("%d/%m/%Y %H:%M"),
            }
            for n in notifications
        ]
        return JsonResponse({"notifications": data})
    except Exception as e:
        print("Error en get_notifications:", e)
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_POST
@csrf_exempt
def mark_notification_seen(request):    
    notification_id = request.POST.get("notification_id")
    try:
        notification = request.user.notifications.get(id=notification_id)
        notification.seen = True
        notification.save()
        return JsonResponse({"success": True})
    except Notification.DoesNotExist:
        return JsonResponse({"success": False, "error": "Notificación no encontrada"})