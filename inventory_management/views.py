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
        domain = "https://localhost:8000"
        # equipos_con_qr = []
        for eq in equipos:
            public_url = f"{domain}/got/public/equipo/{eq.code}/"

            # detail_url = f"/got/systems/{eq.system.pk}/{eq.code}/"

            # Crear el QRCode
            # qr = qrcode.QRCode(version=1, box_size=4, border=2)
            # qr.add_data(detail_url)
            # qr.make(fit=True)

            qr = qrcode.QRCode(version=1, box_size=4, border=2)
            qr.add_data(public_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            # Convertir la imagen a base64
            qr_io = BytesIO()
            img.save(qr_io, format='PNG')
            eq.qr_code_b64 = base64.b64encode(qr_io.getvalue()).decode('utf-8')

        context = {
            'activo': activo,
            'all_activos': all_activos,   # Para el scroll horizontal
            'equipos': equipos,           # Para la tabla de equipos
            # 'equipos_qr': equipos_con_qr,
            'suministros': suministros,   # Para la tabla de suministros
        }

        return render(request, self.template_name, context)
    


def public_equipo_detail(request, eq_code):
    """
    Vista pública (sin login) con la info completa de un equipo.
    No muestra la barra de navegación, etc.
    """
    equipo = get_object_or_404(Equipo, code=eq_code)
    # Podrías traer imágenes, rutinas, etc.:
    images = equipo.images.all()
    # O si quieres más datos:
    # rutinas = Ruta.objects.filter(equipo=equipo) ...
    # ...
    return render(request, 'inventory_management/public_equipo_detail.html', {
        'equipo': equipo,
        'images': images,
        # 'rutinas': rutinas, etc.
    })