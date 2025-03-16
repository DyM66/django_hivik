// static/js/service_worker.js

// Escucha el evento push para mostrar una notificación
self.addEventListener('push', function(event) {
    let data = {};
    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            data = { title: 'Notificación', message: event.data.text() };
        }
    }
    const title = data.title || 'Notificación';
    const options = {
        body: data.message || 'Tienes una nueva notificación.',
        icon: data.icon || '/static/tu-icono.png',  // Asegúrate de tener un icono en esta ruta
        data: {
            url: data.redirect_url || '/'
        }
    };
    event.waitUntil(self.registration.showNotification(title, options));
});
  
// Escucha el evento click en la notificación
self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
            for (const client of clientList) {
                if (client.url === event.notification.data.url && 'focus' in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(event.notification.data.url);
            }
        })
    );
  });
  