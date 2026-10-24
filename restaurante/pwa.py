"""Recursos públicos do PWA, sem contexto de usuário ou tokens CSRF no cache."""
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.templatetags.static import static


def manifest(request):
    response = JsonResponse({
        'id': '/', 'name': 'MesaFácil', 'short_name': 'MesaFácil', 'lang': 'pt-BR',
        'description': 'Cardápio e acompanhamento de pedidos por QR Code.',
        'start_url': '/', 'scope': '/', 'display': 'standalone',
        'background_color': '#fbf8f2', 'theme_color': '#ae452c',
        'icons': [
            {'src': static('icons/icon-192.png'), 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any'},
            {'src': static('icons/icon-512.png'), 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any'},
            {'src': static('icons/maskable-512.png'), 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
        ],
    }, content_type='application/manifest+json')
    response['Cache-Control'] = 'public, max-age=600'
    return response


def offline(request):
    # Não usar request no render: a página pública não pode carregar dados do login.
    response = HttpResponse(render_to_string('offline.html'))
    response['Cache-Control'] = 'public, max-age=600'
    return response


def service_worker(request):
    response = HttpResponse(render_to_string('service-worker.js'), content_type='application/javascript')
    response['Cache-Control'] = 'no-cache'
    response['Service-Worker-Allowed'] = '/'
    return response
