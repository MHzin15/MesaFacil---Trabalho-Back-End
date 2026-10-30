"""
URL configuration for core project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.contrib.auth import views as auth_views
from restaurante import pages, pwa
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path('manifest.webmanifest', pwa.manifest, name='manifest'),
    path('service-worker.js', pwa.service_worker, name='service-worker'),
    path('offline/', pwa.offline, name='offline'),
    path('media/produtos/<path:path>', pages.foto_produto, name='foto-produto'),
    path('', pages.inicio, name='inicio'),
    path('mesa/<uuid:uuid>/', pages.cliente, name='cliente'),
    path('mesa/<uuid:uuid>/carrinho/', pages.cliente, {'tela': 'carrinho'}, name='cliente-carrinho'),
    path('mesa/<uuid:uuid>/pedidos/', pages.cliente, {'tela': 'pedidos'}, name='cliente-pedidos'),
    path('mesa/<uuid:uuid>/conta/', pages.cliente, {'tela': 'conta'}, name='cliente-conta'),
    path('cozinha/', pages.cozinha, name='cozinha'),
    path('cozinha/disponibilidade/', pages.cozinha, {'tela': 'disponibilidade'}, name='cozinha-disponibilidade'),
    path('garcom/', pages.garcom, name='garcom'),
    path('garcom/entregas/', pages.garcom, {'tela': 'entregas'}, name='garcom-entregas'),
    path('garcom/contas/', pages.garcom, {'tela': 'contas'}, name='garcom-contas'),
    path('painel/', pages.painel, name='painel'),
    path('entrar/', auth_views.LoginView.as_view(), name='login'),
    path('sair/', auth_views.LogoutView.as_view(), name='logout'),
    path('admin/', admin.site.urls),
    path('api/', include('restaurante.urls')),

    # Documentação da API (drf-spectacular)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
