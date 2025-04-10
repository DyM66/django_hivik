from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from preoperacionales.models import *
from preoperacionales.forms import *
from django.utils.translation import gettext as _


class DepartureAuthorizationView(LoginRequiredMixin, View):
    template_name = "preoperacional/departure_authorization.html"

    def get(self, request):
        action = request.GET.get("action", "exit")

        if action == "exit":
            requestedVehicles = Vehicle.objects.filter(status="REQUESTED").order_by(
                "brand"
            )
            for vehicle in requestedVehicles:
                vehicle.comment = vehicle.last_comment

            occupiedVehicles = []
        else:
            requestedVehicles = []
            occupiedVehicles = Vehicle.objects.filter(status="OCCUPIED").order_by(
                "brand"
            )

            print("entry", occupiedVehicles)

        return render(
            request,
            self.template_name,
            {
                "requestedVehicles": requestedVehicles,
                "occupiedVehicles": occupiedVehicles,
                "action": action,
            },
        )

    def post(self, request, action, vehicle_code):

        vehicle = get_object_or_404(Vehicle, code=vehicle_code)

        if action == "exit":
            VehicleMovementHistory.objects.create(
                vehicle=vehicle,
                action="EXIT",
                requested_by=vehicle.requested_by,
                comment=vehicle.last_comment,
            )
            vehicle.status = "OCCUPIED"
        elif action == "reject_exit":
            vehicle.status = "AVAILABLE"
            vehicle.requested_by = ""
        elif action == "entry":
            VehicleMovementHistory.objects.create(
                vehicle=vehicle,
                action="ENTRY",
                requested_by=vehicle.requested_by,
            )
            vehicle.status = "AVAILABLE"
            vehicle.requested_by = ""
            vehicle.last_comment = ""

        vehicle.save()

        url = reverse("preoperacionales:departure_authorization")
        if action == "entry":
            urlWithParams = f"{url}?action=entry"
        else:
            urlWithParams = f"{url}?action=exit"
        return redirect(urlWithParams)
