// static/js/service_worker.js

// Escucha el evento push para mostrar una notificación
self.addEventListener('push', event => {
    let data = event.data.json();
    const title = data.title || 'GOT SERPORT';
    const options = {
        body: data.message,
        icon: data.icon || 'https://hivik.s3.us-east-2.amazonaws.com/static/Outlook-fdeyoovu.png',
        data: {url: data.redirect_url || '/'}
    };
    event.waitUntil(self.registration.showNotification(title, options));
});
  
self.addEventListener('notificationclick', event => {
    event.notification.close();
    event.waitUntil(clients.openWindow(event.notification.data.url));
});