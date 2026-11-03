"""Páginas Django; as interações consomem a mesma API REST documentada."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
from django.http import Http404
from django.views.static import serve
from django.views.decorators.csrf import ensure_csrf_cookie
from PIL import Image, UnidentifiedImageError

from .models import Mesa
from .security import vincular_mesa, usuario_garcom, equipe_mesa


def foto_produto(request, path):
    """Apenas fotos públicas; nunca o diretório de QR Codes ou o restante da mídia."""
    response = serve(request, path, document_root=settings.MEDIA_ROOT / 'produtos')
    if response.status_code == 200:
        # Arquivos legados/importados podem não ter passado pelos formulários.
        # O navegador deve receber o tipo dos bytes, nunca o da extensão.
        stream = response.file_to_stream
        try:
            image = Image.open(stream)
            content_type = Image.MIME.get(image.format, 'application/octet-stream')
            response['Content-Type'] = content_type
            stream.seek(0)
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            # Não emitir request_finished antes de o Django construir o 404.
            stream.close()
            raise Http404('Imagem inválida.') from None
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "default-src 'none'; sandbox"
    return response


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
    modo_garcom = equipe_mesa(request.user)
    if modo_garcom and tela == 'carrinho':
        return redirect('cliente-pedidos', uuid=mesa.token_uuid)
    if request.GET.get('bloqueado') != '1':
        vincular_mesa(request, mesa)
    mesa.refresh_from_db()
    from .security import acesso_mesa, chave_comanda, comanda_cliente
    from .atendimento import ocupada, revogado
    if not modo_garcom and not acesso_mesa(request, mesa):
        antiga = comanda_cliente(request, mesa)
        response = render(request, 'restaurante/mesa_ocupada.html', {
            'mesa': mesa, 'ocupada': ocupada(mesa),
            'encerrado': bool((antiga and not antiga.ativa) or revogado(mesa, chave_comanda(request, mesa))),
        })
        response['Cache-Control'] = 'no-store'
        response['Referrer-Policy'] = 'same-origin'
        return response
    titulos = {
        'cardapio': ('Cardápio', 'Escolha seus produtos e personalize cada item.'),
        'carrinho': ('Seu carrinho', 'Confira as quantidades e os adicionais antes de enviar.'),
        'pedidos': ('Meus pedidos', 'Acompanhe o preparo e a entrega dos pedidos da sua comanda.'),
        'conta': ('Minha conta', 'Veja o total da sua comanda e peça o fechamento quando quiser.'),
    }
    if modo_garcom:
        titulos.update({
            'cardapio': ('Cardápio', 'Consulte os produtos disponíveis para esta mesa.'),
            'pedidos': ('Pedidos', 'Acompanhe o preparo e a entrega dos pedidos da sua comanda.'),
            'conta': ('Contas', 'Confira o consumo da mesa e acesse o fechamento no salão.'),
        })
    titulo, descricao = titulos[tela]
    response = render(request, 'restaurante/cliente.html', {
        'mesa': mesa, 'cliente_tela': tela,
        'modo_garcom': modo_garcom,
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
        'mesas': ('Mesas do salão', 'O cliente começa pelo QR. Acompanhe as mesas e confira cada conta.'),
        'entregas': ('Entregas', 'Retire os pedidos prontos e confirme quando chegarem à mesa.'),
        'contas': ('Contas solicitadas', 'Confira os pedidos da mesa e finalize o atendimento.'),
    }
    titulo, descricao = telas[tela]
    return render(request, 'restaurante/garcom.html', {
        'equipe_area': 'garcom', 'equipe_tela': tela, 'equipe_titulo': titulo, 'equipe_descricao': descricao,
    })
