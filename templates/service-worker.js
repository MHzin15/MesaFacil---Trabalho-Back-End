{% load static %}
'use strict';
const CACHE = 'mesafacil-public-v5';
const OFFLINE = '/offline/';
const ASSETS = [OFFLINE, '/manifest.webmanifest',
  '{% static "js/offline.js" %}', '{% static "css/style.css" %}', '{% static "css/cliente.css" %}', '{% static "css/equipe.css" %}', '{% static "vendor/bootstrap.min.css" %}',
  '{% static "icons/icon-192.png" %}', '{% static "icons/icon-512.png" %}',
  '{% static "icons/maskable-512.png" %}'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k.startsWith('mesafacil-public-') && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;

  // HTML é sempre buscado na rede; offline só pode devolver a página pública.
  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).catch(() => caches.match(OFFLINE)));
    return;
  }
  if (url.pathname === '/api/cardapio/' && !url.search) {
    event.respondWith((async () => {
      const cache = await caches.open(CACHE);
      try {
        const response = await fetch(request);
        if (response.ok) await cache.put('/api/cardapio/', response.clone());
        return response;
      } catch {
        return (await cache.match('/api/cardapio/')) || new Response(JSON.stringify({erro:'Cardápio ainda não disponível offline.'}), {status:503, headers:{'Content-Type':'application/json'}});
      }
    })());
    return;
  }
  if (url.pathname.startsWith('/static/') || url.pathname === '/manifest.webmanifest') {
    event.respondWith((async () => {
      const cache = await caches.open(CACHE);
      const stored = await cache.match(request);
      // Arquivos com hash são imutáveis. Sem hash, buscar a versão atual evita
      // manter CSS/JS antigos durante o desenvolvimento local.
      if (stored && /\.[a-f0-9]{12}\./.test(url.pathname)) return stored;
      try {
        const response = await fetch(request);
        if (response.ok && response.type === 'basic') await cache.put(request, response.clone());
        return response;
      } catch { return stored || Response.error(); }
    })());
  }
  // API privada, imagens de QR e qualquer escrita nunca entram no Cache API.
});
