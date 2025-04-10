from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from preoperacionales.models import *
from preoperacionales.forms import *
from preoperacionales.mixins import DriversAdminRequiredMixin
from django.utils.translation import gettext as _


class VehicleAdminView(DriversAdminRequiredMixin, View):
    template_name = "preoperacional/vehicle_admin.html"

    def get(self, request, vehicle_code):
        # Buscar el vehículo usando el código proporcionado en la URL
        try:
            vehicle = Vehicle.objects.get(code=vehicle_code)
            preoperacionales_diario = PreoperacionalDiario.objects.filter(
                vehiculo=vehicle.code
            ).order_by("-fecha")
            preoperacionales_especifico = Preoperacional.objects.filter(
                vehiculo=vehicle.code
            ).order_by("-fecha")
        except Vehicle.DoesNotExist:
            # Si no se encuentra el vehículo, redirigir o mostrar un error
            return render(request, "preoperacional/vehicle_not_found.html")

        STATUS_CHOICES = [
            ("AVAILABLE", "Disponible"),
            ("UNDER_MAINTENANCE", "En Mantenimiento"),
            ("OUT_OF_SERVICE", "Fuera de Servicio"),
            ("RESERVED_FOR_MANAGEMENT", "Reservado para Gerencia"),
        ]

        preoperacionales_con_next_prev = []

        for i, preoperacional in enumerate(preoperacionales_especifico):
            # Obtener el preoperacional anterior (si existe)
            if i > 0:
                preoperacional.next = preoperacionales_especifico[i - 1]
            else:
                preoperacional.next = None

            # Obtener el siguiente preoperacional (si existe)
            if i < len(preoperacionales_especifico) - 1:
                preoperacional.previous = preoperacionales_especifico[i + 1]
            else:
                preoperacional.previous = None

            preoperacionales_con_next_prev.append(preoperacional)

        # Pasar el vehículo encontrado al template
        return render(
            request,
            self.template_name,
            {
                "vehicle": vehicle,
                "status_choices": STATUS_CHOICES,
                "preoperacionales_diario": preoperacionales_diario,
                "preoperacionales_especifico": preoperacionales_con_next_prev,
            },
        )

    def post(self, request, vehicle_code):

        fullname = request.user.get_full_name()
        vehicle_code = request.POST.get("vehicle_code")
        vehicle = get_object_or_404(Vehicle, code=vehicle_code)

        status_transitions = {
            "UNDER_MAINTENANCE": "MAINTENANCE_IN",
            "OUT_OF_SERVICE": "SERVICE_OUT",
            ("OCCUPIED", "AVAILABLE"): "ENTRY",
            ("UNDER_MAINTENANCE", "AVAILABLE"): "MAINTENANCE_OUT",
            ("OUT_OF_SERVICE", "AVAILABLE"): "SERVICE_IN",
        }

        new_status = request.POST.get("status")

        if new_status == "RESERVED_FOR_MANAGEMENT":
            vehicle.requested_by = "GERENCIA"
            vehicle.last_comment = request.POST.get("comment")
            vehicle.status = "REQUESTED"
        else:
            # Determinar la acción basada en la transición del estado
            action = status_transitions.get(
                (vehicle.status, new_status)
            ) or status_transitions.get(new_status)
            vehicle.status = request.POST.get("status")

            # Si hay una acción válida, registrar el historial
            if action:
                VehicleMovementHistory.objects.create(
                    vehicle=vehicle,
                    action=action,
                    requested_by=fullname,
                    comment=request.POST.get("comment"),
                )

        vehicle.save()
        return redirect(
            reverse(
                "preoperacionales:vehicle_admin", kwargs={"vehicle_code": vehicle_code}
            )
        )
