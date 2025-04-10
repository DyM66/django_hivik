from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from preoperacionales.models import *
from preoperacionales.forms import *
from preoperacionales.mixins import DriversAdminRequiredMixin
from got.models import Equipo
from django.utils.translation import gettext as _


class AdminView(DriversAdminRequiredMixin, View):
    template_name = "preoperacional/admin.html"

    def get(self, request):

        vehicles = Vehicle.objects.order_by("status")
        for vehicle in vehicles:
            vehicle.history = vehicle.movement_history.all()
            equipo = get_object_or_404(Equipo, code=vehicle.code)
            vehicle.equipo = equipo

        drivers = Driver.objects.all()

        return render(
            request,
            self.template_name,
            {"vehicles": vehicles, "drivers": drivers},
        )

    def post(self, request):
        name = request.POST.get("name")
        surname = request.POST.get("surname")
        id_number = request.POST.get("id_number")

        if not name or not surname or not id_number:
            return redirect(reverse("preoperacionales:admin"))

        # Crear un nuevo conductor
        Driver.objects.create(name=name, surname=surname, id_number=id_number)

        # Redirigir al mismo path
        return redirect(reverse("preoperacionales:admin"))
