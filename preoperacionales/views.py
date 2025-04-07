from datetime import datetime, time, date
from django.db.models import Sum
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.views import generic, View
from django.urls import reverse
from django.utils import timezone
from django.http import Http404
import calendar
from .models import *
from .forms import *
from got.forms import UploadImages
from got.models import Equipo, Image, HistoryHour
from django.utils.translation import gettext as _
from got.utils import pro_export_to_excel
from .models import Vehicle, VehicleMovementHistory
from dth.models import Nomina


class PreoperacionalDetailView(LoginRequiredMixin, generic.DetailView):
    model = PreoperacionalDiario
    template_name = "preoperacional/preoperacional_detail.html"


def preoperacional_diario_view(request, code):

    equipo = get_object_or_404(Equipo, code=code)
    rutas_vencidas = [
        ruta for ruta in equipo.equipos.all() if ruta.next_date < date.today()
    ]

    existente = PreoperacionalDiario.objects.filter(
        vehiculo=equipo, fecha=date.today()
    ).first()

    if existente:
        mensaje = f"El preoperacional del vehículo {equipo} de la fecha actual ya fue diligenciado y exitosamente enviado. El resultado fue: {'Aprobado' if existente.aprobado else 'No aprobado'}."
        messages.error(request, mensaje)
        return render(
            request,
            "preoperacional/preoperacional_restricted.html",
            {"mensaje": mensaje},
        )

    if request.method == "POST":
        form = PreoperacionalDiarioForm(
            request.POST, equipo_code=equipo.code, user=request.user
        )
        image_form = UploadImages(request.POST, request.FILES)
        if form.is_valid() and image_form.is_valid():
            preop = form.save(commit=False)
            preop.reporter = request.user if request.user.is_authenticated else None
            preop.vehiculo = equipo
            preop.kilometraje = form.cleaned_data["kilometraje"]
            preop.save()

            horometro_actual = equipo.initial_hours + (
                equipo.hours.filter(report_date__lt=date.today()).aggregate(
                    total=Sum("hour")
                )["total"]
                or 0
            )
            kilometraje_reportado = preop.kilometraje - horometro_actual

            history_hour, created = HistoryHour.objects.get_or_create(
                component=equipo,
                report_date=date.today(),
                defaults={"hour": kilometraje_reportado},
            )

            if not created:
                history_hour.hour = kilometraje_reportado
                history_hour.save()

            equipo.horometro = preop.kilometraje
            equipo.save()

            for file in request.FILES.getlist("file_field"):
                Image.objects.create(preoperacionaldiario=preop, image=file)

            return redirect("preoperacionales:gracias", code=equipo.code)
    else:
        form = PreoperacionalDiarioForm(equipo_code=equipo.code, user=request.user)
        image_form = UploadImages()

    return render(
        request,
        "preoperacional/preoperacionalform.html",
        {
            "vehiculo": equipo,
            "form": form,
            "image_form": image_form,
            "rutas_vencidas": rutas_vencidas,
            "pre": True,
        },
    )


class PreoperacionalDiarioUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = PreoperacionalDiario
    form_class = PreoperacionalDiarioForm
    template_name = "preoperacional/preoperacionalform.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        preoperacional = self.get_object()
        kwargs["equipo_code"] = preoperacional.vehiculo.code
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        preoperacional = form.instance
        equipo = preoperacional.vehiculo
        fecha_preoperacional = preoperacional.fecha
        horometro_actual = equipo.initial_hours + (
            equipo.hours.exclude(report_date=fecha_preoperacional).aggregate(
                total=Sum("hour")
            )["total"]
            or 0
        )
        kilometraje_reportado = form.cleaned_data["kilometraje"] - horometro_actual

        history_hour, _ = HistoryHour.objects.get_or_create(
            component=equipo,
            report_date=preoperacional.fecha,
            defaults={"hour": kilometraje_reportado},
        )

        history_hour.hour = kilometraje_reportado
        history_hour.save()

        equipo.horometro = form.cleaned_data["kilometraje"]
        equipo.save()

        return response

    def get_success_url(self):
        return reverse(
            "preoperacionales:preoperacional-detail", kwargs={"pk": self.object.pk}
        )


class SalidaListView(LoginRequiredMixin, generic.ListView):
    model = Preoperacional
    paginate_by = 15
    template_name = "preoperacional/salida_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obtener la fecha actual
        fecha_actual = timezone.now()

        # Generar rangos de meses y años
        meses = [
            (i, _(calendar.month_name[i])) for i in range(1, 13)
        ]  # De enero a diciembre
        anios = range(
            fecha_actual.year - 5, fecha_actual.year + 1
        )  # Últimos 5 años hasta el actual

        # Pasar estos valores al contexto
        context["fecha_actual"] = fecha_actual
        context["meses"] = meses
        context["anios"] = anios

        return context


class SalidaDetailView(LoginRequiredMixin, generic.DetailView):

    model = Preoperacional
    template_name = "preoperacional/salida_detail.html"


"PREOPERACIONAL VIEW"


def export_preoperacional_to_excel(request):
    # Obtener el mes y año del request
    mes = int(request.GET.get("mes", datetime.now().month))
    anio = int(request.GET.get("anio", datetime.now().year))

    preoperacional_diarios = PreoperacionalDiario.objects.filter(
        fecha__year=anio, fecha__month=mes
    )

    headers = [
        "Fecha",
        "Vehículo",
        "Responsable",
        "Kilometraje",
        "Nivel de Combustible",
        "Nivel de Aceite",
        "Nivel de Refrigerante",
        "Nivel de Hidráulico",
        "Nivel de Líquido de Frenos",
        "Poleas",
        "Correas",
        "Mangueras",
        "Acoples",
        "Tanques",
        "Radiador",
        "Terminales",
        "Bujes",
        "Rótulas",
        "Ejes",
        "Cruceta",
        "Puertas",
        "Chapas",
        "Manijas",
        "Elevavidrios",
        "Lunas",
        "Espejos",
        "Vidrio Panorámico",
        "Asiento",
        "Apoyacabezas",
        "Cinturón",
        "Aire",
        "Caja de Cambios",
        "Dirección",
        "Batería",
        "Luces Altas",
        "Luces Medias",
        "Luces Direccionales",
        "Cocuyos",
        "Luz de Placa",
        "Luz Interna",
        "Pito",
        "Alarma de Retroceso",
        "Arranque",
        "Alternador",
        "Rines",
        "Tuercas",
        "Esparragos",
        "Freno de Servicio",
        "Freno de Seguridad",
        "Llanta de Repuesto",
        "Llantas",
        "Suspensión",
        "Capó",
        "Persiana",
        "Bumper Delantero",
        "Parabrisas",
        "Guardafango",
        "Stop",
        "Bumper Trasero",
        "Vidrio Panorámico Trasero",
        "Placa Delantera",
        "Placa Trasera",
        "Aseo Externo",
        "Aseo Interno",
        "Kit de Carreteras",
        "Kit de Herramientas",
        "Kit de Botiquín",
        "Chaleco Reflectivo",
        "Aprobado",
        "Observaciones",
    ]

    data = []
    for preop in preoperacional_diarios:
        fila = [
            preop.fecha.strftime("%d/%m/%Y"),
            preop.vehiculo.name,
            (
                f"{preop.reporter.first_name} {preop.reporter.last_name}"
                if preop.reporter
                else preop.nombre_no_registrado
            ),
            preop.kilometraje,
            preop.get_combustible_level_display(),
            preop.get_aceite_level_display(),
            preop.get_refrigerante_level_display(),
            preop.get_hidraulic_level_display(),
            preop.get_liq_frenos_level_display(),
            preop.get_poleas_display(),
            preop.get_correas_display(),
            preop.get_mangueras_display(),
            preop.get_acoples_display(),
            preop.get_tanques_display(),
            preop.get_radiador_display(),
            preop.get_terminales_display(),
            preop.get_bujes_display(),
            preop.get_rotulas_display(),
            preop.get_ejes_display(),
            preop.get_cruceta_display(),
            preop.get_puertas_display(),
            preop.get_chapas_display(),
            preop.get_manijas_display(),
            preop.get_elevavidrios_display(),
            preop.get_lunas_display(),
            preop.get_espejos_display(),
            preop.get_vidrio_panoramico_display(),
            preop.get_asiento_display(),
            preop.get_apoyacabezas_display(),
            preop.get_cinturon_display(),
            preop.get_aire_display(),
            preop.get_caja_cambios_display(),
            preop.get_direccion_display(),
            preop.get_bateria_display(),
            preop.get_luces_altas_display(),
            preop.get_luces_medias_display(),
            preop.get_luces_direccionales_display(),
            preop.get_cocuyos_display(),
            preop.get_luz_placa_display(),
            preop.get_luz_interna_display(),
            preop.get_pito_display(),
            preop.get_alarma_retroceso_display(),
            preop.get_arranque_display(),
            preop.get_alternador_display(),
            preop.get_rines_display(),
            preop.get_tuercas_display(),
            preop.get_esparragos_display(),
            preop.get_freno_servicio_display(),
            preop.get_freno_seguridad_display(),
            "Sí" if preop.is_llanta_repuesto else "No",
            preop.get_llantas_display(),
            preop.get_suspencion_display(),
            preop.get_capo_display(),
            preop.get_persiana_display(),
            preop.get_bumper_delantero_display(),
            preop.get_panoramico_display(),
            preop.get_guardafango_display(),
            preop.get_stop_display(),
            preop.get_bumper_trasero_display(),
            preop.get_vidrio_panoramico_trasero_display(),
            preop.get_placa_delantera_display(),
            preop.get_placa_trasera_display(),
            "Sí" if preop.aseo_externo else "No",
            "Sí" if preop.aseo_interno else "No",
            "Sí" if preop.kit_carreteras else "No",
            "Sí" if preop.kit_herramientas else "No",
            "Sí" if preop.kit_botiquin else "No",
            "Sí" if preop.chaleco_reflectivo else "No",
            "Sí" if preop.aprobado else "No",
            preop.observaciones,
        ]
        data.append(fila)

    filename = f"PreoperacionalDiario_{mes}_{anio}.xlsx"
    sheet_name = f"Preoperacional Diario {mes}-{anio}"
    table_title = f"Preoperacional Diario {mes}-{anio}"

    return pro_export_to_excel(
        model=PreoperacionalDiario,
        headers=headers,
        data=data,
        filename=filename,
        sheet_name=sheet_name,
        table_title=table_title,
    )


def export_salidas_to_excel(request):
    from datetime import datetime

    mes = int(request.GET.get("mes", datetime.now().month))
    anio = int(request.GET.get("anio", datetime.now().year))

    preoperacionales = Preoperacional.objects.filter(fecha__month=mes, fecha__year=anio)

    headers = [
        "Fecha",
        "Vehiculo",
        "Responsable",
        "Kilometraje",
        "Salida",
        "Destino",
        "Autorizado",
        "Horas trabajo",
        "Medicamentos",
        "Molestias",
        "Enfermo",
        "Condiciones",
        "Agua",
        "Dormido",
        "Control",
        "Sueño",
        "Radio Aire",
        "Observaciones",
    ]

    data = []
    for preop in preoperacionales:
        fila = [
            preop.fecha.strftime("%d/%m/%Y"),
            str(preop.vehiculo),
            (
                f"{preop.reporter.first_name} {preop.reporter.last_name}"
                if preop.reporter
                else preop.nombre_no_registrado
            ),
            preop.kilometraje,
            preop.salida,
            preop.destino,
            preop.get_autorizado_display(),
            "Sí" if preop.horas_trabajo else "No",
            "Sí" if preop.medicamentos else "No",
            "Sí" if preop.molestias else "No",
            "Sí" if preop.enfermo else "No",
            "Sí" if preop.condiciones else "No",
            "Sí" if preop.agua else "No",
            "Sí" if preop.dormido else "No",
            "Sí" if preop.control else "No",
            "Sí" if preop.sueño else "No",
            "Sí" if preop.radio_aire else "No",
            preop.observaciones,
        ]
        data.append(fila)

    # Título, nombre de hoja y nombre de archivo
    filename = f"Preoperacional_{mes}-{anio}.xlsx"
    sheet_name = f"Preoperacional {mes}-{anio}"
    table_title = f"Preoperacional {mes}-{anio}"

    return pro_export_to_excel(
        model=Preoperacional,  # El modelo que usas
        headers=headers,
        data=data,
        filename=filename,
        sheet_name=sheet_name,
        table_title=table_title,
    )


def preoperacional_especifico_view(request, code):
    equipo = get_object_or_404(Equipo, code=code)
    rutas_vencidas = [
        ruta for ruta in equipo.equipos.all() if ruta.next_date < date.today()
    ]

    if request.method == "POST":
        form = PreoperacionalEspecificoForm(
            request.POST, equipo_code=equipo.code, user=request.user
        )
        image_form = UploadImages(request.POST, request.FILES)
        if form.is_valid() and image_form.is_valid():
            preop = form.save(commit=False)
            preop.reporter = request.user if request.user.is_authenticated else None
            preop.vehiculo = equipo
            nuevo_kilometraje = form.cleaned_data["nuevo_kilometraje"]
            preop.kilometraje = nuevo_kilometraje
            preop.save()

            horometro_actual = equipo.initial_hours + (
                equipo.hours.filter(report_date__lt=date.today()).aggregate(
                    total=Sum("hour")
                )["total"]
                or 0
            )
            kilometraje_reportado = nuevo_kilometraje - horometro_actual

            history_hour, created = HistoryHour.objects.get_or_create(
                component=equipo,
                report_date=date.today(),
                defaults={"hour": kilometraje_reportado},
            )

            if not created:
                history_hour.hour = kilometraje_reportado
                history_hour.save()

            equipo.horometro = nuevo_kilometraje
            equipo.save()

            for file in request.FILES.getlist("file_field"):
                Image.objects.create(preoperacional=preop, image=file)

            # ; ACTUALIZAR EL ESTADO DEL CARRO A SOLICITADO.
            # Buscar el Vehicle con el mismo código y actualizar su estado a REQUESTED
            vehicle = Vehicle.objects.filter(code=equipo.code).first()
            if vehicle:
                vehicle.status = "REQUESTED"
                vehicle.requested_by = (
                    request.user.get_full_name()
                    if request.user.is_authenticated
                    else form.cleaned_data.get("nombre_no_registrado", "Desconocido")
                )
                vehicle.save()

            return redirect("preoperacionales:gracias", code=equipo.code)
    else:
        form = PreoperacionalEspecificoForm(equipo_code=equipo.code, user=request.user)
        image_form = UploadImages()

    return render(
        request,
        "preoperacional/preoperacionalform.html",
        {
            "vehiculo": equipo,
            "form": form,
            "image_form": image_form,
            "rutas_vencidas": rutas_vencidas,
        },
    )


"PREOPERACIONAL DIARIO VIEW"


class PreoperacionalListView(LoginRequiredMixin, generic.ListView):
    model = PreoperacionalDiario
    paginate_by = 15
    template_name = "preoperacional/preoperacional_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obtener la fecha actual
        fecha_actual = timezone.now()

        # Generar rangos de meses y años
        meses = [
            (i, _(calendar.month_name[i])) for i in range(1, 13)
        ]  # De enero a diciembre
        anios = range(
            fecha_actual.year - 5, fecha_actual.year + 1
        )  # Últimos 5 años hasta el actual

        # Pasar estos valores al contexto
        context["fecha_actual"] = fecha_actual
        context["meses"] = meses
        context["anios"] = anios

        return context


def gracias_view(request, code):
    equipo = get_object_or_404(Equipo, code=code)
    return render(request, "preoperacional/gracias.html", {"equipo": equipo})


class PreoperacionalUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = Preoperacional
    form_class = PreoperacionalEspecificoForm
    template_name = "preoperacional/preoperacionalform.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        preoperacional = self.get_object()
        kwargs["equipo_code"] = preoperacional.vehiculo.code
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        preoperacional = form.save(commit=False)
        equipo = preoperacional.vehiculo
        nuevo_kilometraje = form.cleaned_data["nuevo_kilometraje"]
        fecha_preoperacional = preoperacional.fecha

        # Calcular el horómetro actual excluyendo el reporte actual
        horometro_actual = equipo.initial_hours + (
            equipo.hours.exclude(report_date=fecha_preoperacional).aggregate(
                total=Sum("hour")
            )["total"]
            or 0
        )
        kilometraje_reportado = nuevo_kilometraje - horometro_actual

        # Actualizar o crear el registro de horas
        history_hour, _ = HistoryHour.objects.get_or_create(
            component=equipo,
            report_date=fecha_preoperacional,
            defaults={"hour": kilometraje_reportado},
        )

        history_hour.hour = kilometraje_reportado
        history_hour.save()

        # Actualizar el horómetro del equipo
        equipo.horometro = nuevo_kilometraje
        equipo.save()

        preoperacional.save()

        return super().form_valid(form)

    def get_success_url(self):
        return reverse("preoperacionales:salidas-detail", kwargs={"pk": self.object.pk})


class PublicVehicleMenuView(View):
    template_name = "preoperacional/public_vehicle_menu.html"

    def get(self, request):
        user = request.user
        vehicles = Vehicle.objects.order_by("status")
        drivers = Nomina.objects.filter(is_driver=True).values("id_number")
        driver_ids = [driver["id_number"] for driver in drivers]

        vehicles_with_equipment = []

        for vehicle in vehicles:
            system = vehicle.system
            equipo = system.equipos.filter(code=vehicle.code)

            if equipo:
                vehicle.equipo = equipo[0]
            else:
                vehicle.equipo = None

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


class PreoperationalAuthorizationView(LoginRequiredMixin, View):
    template_name = "preoperacional/preoperational_authorization.html"

    def get(self, request):
        action = request.GET.get("action", "exit")

        if action == "exit":
            requestedVehicles = Vehicle.objects.filter(status="REQUESTED").order_by(
                "brand"
            )
            for vehicle in requestedVehicles:
                last_preoperational = (
                    Preoperacional.objects.filter(vehiculo=vehicle.code)
                    .order_by("-fecha")
                    .first()
                )
                vehicle.comment = (
                    last_preoperational.observaciones if last_preoperational else ""
                )

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
            last_preoperational = (
                Preoperacional.objects.filter(vehiculo=vehicle.code)
                .order_by("-fecha")
                .first()
            )
            VehicleMovementHistory.objects.create(
                vehicle=vehicle,
                action="EXIT",
                requested_by=vehicle.requested_by,
                comment=(
                    last_preoperational.observaciones if last_preoperational else ""
                ),
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

        vehicle.save()

        url = reverse("preoperacionales:preoperational_authorization")
        if action == "entry":
            urlWithParams = f"{url}?action=entry"
        else:
            urlWithParams = f"{url}?action=exit"
        return redirect(urlWithParams)


class AdminView(LoginRequiredMixin, View):
    template_name = "preoperacional/admin.html"

    def get(self, request):

        vehicles = Vehicle.objects.order_by("status")
        for vehicle in vehicles:
            vehicle.history = vehicle.movement_history.all()

        return render(
            request,
            self.template_name,
            {
                "vehicles": vehicles,
            },
        )


class VehicleAdminView(LoginRequiredMixin, View):
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
        ]

        # Pasar el vehículo encontrado al template
        return render(
            request,
            self.template_name,
            {
                "vehicle": vehicle,
                "status_choices": STATUS_CHOICES,
                "preoperacionales_diario": preoperacionales_diario,
                "preoperacionales_especifico": preoperacionales_especifico,
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

        # Determinar la acción basada en la transición del estado
        action = status_transitions.get(
            (vehicle.status, new_status)
        ) or status_transitions.get(new_status)

        # Si hay una acción válida, registrar el historial
        if action:
            VehicleMovementHistory.objects.create(
                vehicle=vehicle,
                action=action,
                requested_by=fullname,
                comment=request.POST.get("comment"),
            )

        vehicle.status = request.POST.get("status")

        vehicle.save()
        return redirect(
            reverse(
                "preoperacionales:vehicle_admin", kwargs={"vehicle_code": vehicle_code}
            )
        )
