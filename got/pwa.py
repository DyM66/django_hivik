# got/pwa.py

from django.http import JsonResponse, HttpResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.conf import settings
from inv.models import Solicitud

# Modelos
# from got.models import Solicitud

# Puedes definir una constante para el logo utilizando settings:
PROJECT_LOGO_URL = getattr(settings, 'PROJECT_LOGO_URL', "https://hivik.s3.us-east-2.amazonaws.com/static/Outlook-fdeyoovu.png")

@cache_control(max_age=86400)
def manifest(request):
    # Mejorar la definición del manifest usando PROJECT_LOGO_URL y agregando propiedades útiles
    manifest_data = {
        "name": "GOT",
        "short_name": "GOT",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#FFFFFF",
        "theme_color": "#191645",
        # Agregar scope y orientación si se requiere:
        "scope": "/",
        "orientation": "portrait",
        "icons": [
            {
                "src": PROJECT_LOGO_URL,
                "sizes": "103x101",
                "type": "image/png"
            },
        ],
        # Podrías incluir una versión para forzar actualizaciones cuando cambie el manifest
        "version": "1.0.0"
    }
    return JsonResponse(manifest_data)


@never_cache
def service_worker(request):
    # Este script usa Workbox (importado vía CDN) para:
    # - Precachear recursos estáticos
    # - Configurar Background Sync para peticiones POST a /reportehorasasset/
    js = """
importScripts('https://storage.googleapis.com/workbox-cdn/releases/6.5.3/workbox-sw.js');

if (workbox) {
  console.log("Workbox se ha cargado correctamente.");

  // Precaching: define los recursos críticos (ajusta las rutas y versiones según tus necesidades)
  workbox.precaching.precacheAndRoute([
    { url: '/', revision: '1' },
    { url: '/static/boostrap/css/bootstrap.min.css', revision: '1' },
    // Agrega aquí otros recursos estáticos importantes (JS, CSS, imágenes, etc.)
  ]);

  // Plugin para Background Sync (para peticiones POST, por ejemplo, de reporte de horas)
  const bgSyncPlugin = new workbox.backgroundSync.BackgroundSyncPlugin('reportSyncQueue', {
    maxRetentionTime: 24 * 60  // Retención máxima en minutos (24 horas)
  });

  // Registra una ruta para interceptar peticiones POST a /reportehorasasset/
  workbox.routing.registerRoute(
    new RegExp('/reportehorasasset/'),
    new workbox.strategies.NetworkOnly({
      plugins: [bgSyncPlugin]
    }),
    'POST'
  );

  // Para otros recursos (documentos, estilos, scripts) se aplica una estrategia Cache First
  workbox.routing.registerRoute(
    ({request}) => request.destination === 'document' ||
                   request.destination === 'style' ||
                   request.destination === 'script',
    new workbox.strategies.CacheFirst({
      cacheName: 'static-resources',
      plugins: [
        new workbox.expiration.ExpirationPlugin({
          maxEntries: 50,
          maxAgeSeconds: 7 * 24 * 60 * 60, // 1 semana
        })
      ]
    })
  );

} else {
  console.log("Workbox no se ha cargado.");
}

self.addEventListener('fetch', (event) => {
  // Aquí podrías agregar lógica adicional para peticiones no cubiertas por Workbox
});
    """
    return HttpResponse(js, content_type='application/javascript')