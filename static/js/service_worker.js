// static/js/service_worker.js

// Escucha el evento push para mostrar una notificación
var CACHE_NAME = 'my-site-cache-v2';
var urlsToCache = [
    '/',
];  

self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(function(cache) {
                console.log('Opened cache');
                return cache.addAll(urlsToCache);
            })
    );
});

self.addEventListener('fetch', function(event) {
    event.respondWith(
        fetch(event.request)
        .then(function(result) {
                return caches.open(CACHE_NAME).then(function(c) {
                    c.put(event.request.url, result.clone());
                    return result;
                })
            })
            .catch(function(e){
                return caches.match(event.request)
            })
    );
});


importScripts(
    'https://www.gstatic.com/firebasejs/9.6.10/firebase-app-compat.js',
    'https://www.gstatic.com/firebasejs/9.6.10/firebase-messaging-compat.js'
  );

const firebaseConfig = {
	apiKey: "AIzaSyBet8fl59quq9g-QKOy9WQav6RUfJRtEVI",
	authDomain: "got-serport.firebaseapp.com",
	projectId: "got-serport",
	storageBucket: "got-serport.firebasestorage.app",
	messagingSenderId: "189173234409",
	appId: "1:189173234409:web:1cd69a265d5d37cb584e78"
};
	
const app = initializeApp(firebaseConfig);

let messaging = firebase.messaging();

messaging.setBackgroundMessageHandler(function(payload) {
    let title = 'titulo de la notificación';
    let options = {
        body: 'Este es el mensaje',
        // icon: payload.notification.icon
    };
    
    self.registration.showNotification(title, options);
});