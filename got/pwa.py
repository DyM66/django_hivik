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
                "sizes": "32x32",  # Se puede ajustar o agregar varios tamaños
                "type": "image/png"
            },
            {
                "src": PROJECT_LOGO_URL,
                "sizes": "512x512",
                "type": "image/png"
            }
        ],
        # Podrías incluir una versión para forzar actualizaciones cuando cambie el manifest
        "version": "1.0.0"
    }
    return JsonResponse(manifest_data)

@never_cache
def service_worker(request):
    # Mejorar el service worker: aquí se puede implementar una estrategia de caching
    # como "stale-while-revalidate" o precacheo de recursos.
    js = '''
    // Service Worker básico con estrategia de precacheo
    const CACHE_NAME = 'got-cache-v1';
    const PRECACHE_URLS = [
        '/',
        '/static/boostrap/css/bootstrap.min.css',
        // Agrega aquí otros recursos importantes
    ];

    self.addEventListener('install', event => {
        event.waitUntil(
            caches.open(CACHE_NAME)
                .then(cache => cache.addAll(PRECACHE_URLS))
                .then(self.skipWaiting())
        );
    });

    self.addEventListener('activate', event => {
        event.waitUntil(
            caches.keys().then(cacheNames => {
                return Promise.all(
                    cacheNames.filter(name => name !== CACHE_NAME).map(name => caches.delete(name))
                );
            })
        );
        self.clients.claim();
    });

    self.addEventListener('fetch', event => {
        // Estrategia de cache-first para recursos precacheados
        event.respondWith(
            caches.match(event.request)
                .then(response => response || fetch(event.request))
        );
    });
    '''
    return HttpResponse(js, content_type='application/javascript')

@login_required
def get_unapproved_requests_count(request):
    # Función API para obtener el número de solicitudes no aprobadas.
    count = Solicitud.objects.filter(approved=False).count()
    return JsonResponse({'count': count})
