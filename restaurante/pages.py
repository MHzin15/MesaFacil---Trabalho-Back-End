"""Páginas Django; as interações consomem a mesma API REST documentada."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
from django.views.static import serve
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import Mesa
from .security import vincular_mesa


def foto_produto(request, path):
    """Apenas fotos públicas; nunca o diretório de QR Codes ou o restante da mídia."""
    return serve(request, path, document_root=settings.MEDIA_ROOT / 'produtos')


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
def cliente(request, uuid, tela='cardapio'):
    mesa = get_object_or_404(Mesa, token_uuid=uuid, ativa=True)
    vincular_mesa(request, mesa)
    titulos = {
        'cardapio': ('Cardápio', 'Escolha seus produtos e personalize cada item.'),
        'carrinho': ('Seu carrinho', 'Confira as quantidades e os adicionais antes de enviar.'),
        'pedidos': ('Meus pedidos', 'Acompanhe o preparo e a entrega dos pedidos desta mesa.'),
        'conta': ('Conta da mesa', 'Veja o total do atendimento e peça o fechamento quando quiser.'),
    }
    titulo, descricao = titulos[tela]
    response = render(request, 'restaurante/cliente.html', {
        'mesa': mesa, 'cliente_tela': tela,
        'cliente_titulo': titulo, 'cliente_descricao': descricao,
    })
    response['Cache-Control'] = 'no-store'
    response['Referrer-Policy'] = 'same-origin'
    return response


@equipe('ADMIN', 'COZINHA')
@ensure_csrf_cookie
def cozinha(request, tela='fila'):
    telas = {
        'fila': ('Fila de preparo', 'Aceite os pedidos, acompanhe o preparo e avise quando estiverem prontos.'),
        'disponibilidade': ('Disponibilidade dos produtos', 'Mantenha o cardápio atualizado para quem está fazendo pedidos.'),
    }
    titulo, descricao = telas[tela]
    return render(request, 'restaurante/cozinha.html', {
        'equipe_area': 'cozinha', 'equipe_tela': tela, 'equipe_titulo': titulo, 'equipe_descricao': descricao,
    })


@login_required
def painel(request):
    perfil = getattr(request.user, 'perfil', None)
    destinos = {'ADMIN': '/admin/', 'COZINHA': '/cozinha/', 'GARCOM': '/garcom/'}
    if not perfil:
        raise PermissionDenied('Peça ao administrador para definir seu perfil.')
    return redirect(destinos[perfil.role])


@equipe('ADMIN', 'GARCOM')
@ensure_csrf_cookie
def garcom(request, tela='mesas'):
    telas = {
        'mesas': ('Mesas do salão', 'Abra o atendimento e acompanhe a situação de cada mesa.'),
        'entregas': ('Entregas', 'Retire os pedidos prontos e confirme quando chegarem à mesa.'),
        'contas': ('Contas solicitadas', 'Confira os pedidos da mesa e finalize o atendimento.'),
    }
    titulo, descricao = telas[tela]
    return render(request, 'restaurante/garcom.html', {
        'equipe_area': 'garcom', 'equipe_tela': tela, 'equipe_titulo': titulo, 'equipe_descricao': descricao,
    })
