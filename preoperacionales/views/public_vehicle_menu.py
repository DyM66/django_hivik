from datetime import datetime
from django.shortcuts import render
from django.views import View
from preoperacionales.models import *
from preoperacionales.forms import *
from django.utils.translation import gettext as _


class PublicVehicleMenuView(View):
    template_name = "preoperacional/public_vehicle_menu.html"

    def get(self, request):
        user = request.user
        vehicles = Vehicle.objects.order_by("status")
        drivers = Driver.objects.all().values("id_number")
        driver_ids = [driver["id_number"] for driver in drivers]

        vehicles_with_equipment = []

        for vehicle in vehicles:
            system = vehicle.system
            equipo = system.equipos.filter(code=vehicle.code)

            if equipo:
                vehicle.equipo = equipo[0]
            else:
                vehicle.equipo = None

            # Validar si ya se realizó el preoperacional hoy
            current_date = datetime.today().date()  # Fecha actual
            preoperacional_diario = PreoperacionalDiario.objects.filter(
                vehiculo=vehicle.equipo, fecha=current_date
            ).exists()

            # Añadir al vehículo si ya se realizó el preoperacional
            vehicle.preoperational_completed = preoperacional_diario

            vehicles_with_equipment.append(vehicle)

        return render(
            request,
            self.template_name,
            {
                "vehicles": vehicles_with_equipment,
                "driver_ids": driver_ids,
                "user": user,
            },
        )
