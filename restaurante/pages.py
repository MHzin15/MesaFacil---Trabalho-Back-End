"""Páginas Django; as interações consomem a mesma API REST documentada."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import Mesa
from .security import vincular_mesa


def equipe(*roles):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            perfil = getattr(request.user, 'perfil', None)
            if not perfil or perfil.role not in roles:
                raise PermissionDenied('Seu perfil não permite acessar este painel.')
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


def inicio(request):
    return render(request, 'restaurante/inicio.html')


@ensure_csrf_cookie
def cliente(request, uuid):
    mesa = get_object_or_404(Mesa, token_uuid=uuid, ativa=True)
    vincular_mesa(request, mesa)
    response = render(request, 'restaurante/cliente.html', {'mesa': mesa})
    response['Cache-Control'] = 'no-store'
    response['Referrer-Policy'] = 'same-origin'
    return response


@equipe('ADMIN', 'COZINHA')
@ensure_csrf_cookie
def cozinha(request):
    return render(request, 'restaurante/cozinha.html')


@login_required
def painel(request):
    perfil = getattr(request.user, 'perfil', None)
    destinos = {'ADMIN': '/admin/', 'COZINHA': '/cozinha/', 'GARCOM': '/garcom/'}
    if not perfil:
        raise PermissionDenied('Peça ao administrador para definir seu perfil.')
    return redirect(destinos[perfil.role])


@equipe('ADMIN', 'GARCOM')
@ensure_csrf_cookie
def garcom(request):
    return render(request, 'restaurante/garcom.html')
