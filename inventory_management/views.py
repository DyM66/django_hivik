# inventory_management/views.py
import base64
import qrcode
import qrcode.image.svg  # si prefieres SVG
from io import BytesIO
from django.core.files.base import ContentFile

from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.urls import reverse
from django.http import HttpResponseRedirect
from got.models import Asset, System, Equipo, Suministro  # ← Importamos de la app "got"
from django.views import View

class AssetListView(ListView):
    model = Asset
    template_name = 'inventory_management/asset_list.html'
    context_object_name = 'assets'

    def get_queryset(self):
        """
        Excluimos las áreas 'b' (Buceo), 'o' (Oceanografía) y 'x' (Apoyo).
        Filtramos show=True.
        """
        qs = super().get_queryset()
        qs = qs.filter(show=True).exclude(area__in=['b','o','x'])
        return qs.select_related('supervisor','capitan')


#######################################
# Nueva vista: Vista de equipos por asset
#######################################
class ActivoEquipmentListView(View):
    template_name = 'inventory_management/asset_equipment_list.html'

    def get(self, request, abbreviation):
        """
        Muestra un scroll horizontal de todos los Activos (excluyendo b, o, x),
        y a la derecha o abajo la lista de Equipos para el Activo seleccionado,
        junto con la tabla de Suministros, etc.
        """
        # 1) Lista de Activos (excluyendo area b, o, x), show=True
        #    Ordenados por nombre. Utilizamos select_related para traer supervisor/capitan.
        all_activos = (
            Asset.objects.filter(show=True)
            .exclude(area__in=['b', 'o', 'x'])
            .select_related('supervisor', 'capitan')
            .order_by('name')
        )

        # 2) Obtener el Activo seleccionado por abbreviation
        activo = get_object_or_404(Asset, abbreviation=abbreviation)

        # 3) Tomar todos los sistemas del Activo
        sistemas = activo.system_set.all()

        # 4) Listar equipos de dichos sistemas
        equipos = Equipo.objects.filter(system__in=sistemas).order_by('name')

        # 5) Suministros ligados a este Activo
        suministros = Suministro.objects.filter(asset=activo).select_related('item')


        # 6) Generar un QR para cada equipo en base64
        equipos_con_qr = []
        for eq in equipos:
            # Construir la URL final para la vista:
            # /systems/<pk>/?view_type=<eq.code>
            # pk = eq.system.pk  (asumiendo eq.system no es None)
            detail_url = f"/got/systems/{eq.system.pk}/{eq.code}/"

            # Crear el QRCode
            qr = qrcode.QRCode(version=1, box_size=4, border=2)
            qr.add_data(detail_url)
            qr.make(fit=True)

            # Generar imagen en PNG
            img = qr.make_image(fill_color="black", back_color="white")

            # Convertir a binario
            qr_io = BytesIO()
            img.save(qr_io, format='PNG')

            # IMPORTANTE: usar base64 para generar data:image/png;base64, ...
            encoded = base64.b64encode(qr_io.getvalue()).decode('utf-8')
            qr_base64 = "data:image/png;base64," + encoded

            equipos_con_qr.append({
                'obj': eq,          # El objeto Equipo
                'qr_code': qr_base64,  # El string base64
            })

        context = {
            'activo': activo,
            'all_activos': all_activos,   # Para el scroll horizontal
            'equipos': equipos,           # Para la tabla de equipos
            'equipos_qr': equipos_con_qr,
            'suministros': suministros,   # Para la tabla de suministros
        }

        return render(request, self.template_name, context)