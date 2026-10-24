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
    path('cozinha/', pages.cozinha, name='cozinha'),
    path('garcom/', pages.garcom, name='garcom'),
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
