import io
import qrcode
from decimal import Decimal

from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import IntegrityError, transaction
from django.http import HttpResponse

from rest_framework import viewsets, status, generics, serializers
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import (
    Perfil, Mesa, SessaoMesa, Categoria, Produto, Adicional,
    Pedido, ItemPedido, ItemPedidoAdicional, HistoricoStatusPedido, Conta,
)
from .serializers import (
    PerfilSerializer,
    MesaSerializer, MesaClienteSerializer,
    SessaoMesaSerializer,
    CategoriaSerializer, CategoriaComProdutosSerializer,
    ProdutoSerializer, AdicionalSerializer,
    PedidoSerializer, PedidoCriarSerializer, PedidoStatusSerializer,
    PedidoCozinhaSerializer, ProdutoDisponibilidadeSerializer,
    ItemPedidoSerializer,
    HistoricoStatusPedidoSerializer,
    ContaSerializer, PagamentoSerializer,
)
from .permissions import IsAdmin, IsCozinha, IsGarcom, IsEquipe, IsCozinhaOuAdmin, IsGarcomOuAdmin


# ============================================================
# Cardápio — Público (RF05–RF07)
# ============================================================
class CategoriaViewSet(viewsets.ModelViewSet):
    """CRUD de categorias. Leitura pública, escrita para Admin."""
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        return [IsAdmin()]


class ProdutoViewSet(viewsets.ModelViewSet):
    """CRUD de produtos. Leitura pública, escrita para Admin."""
    queryset = Produto.objects.select_related('categoria').prefetch_related('adicionais').all()
    serializer_class = ProdutoSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        return [IsAdmin()]


class AdicionalViewSet(viewsets.ModelViewSet):
    """CRUD de adicionais. Leitura pública, escrita para Admin."""
    queryset = Adicional.objects.select_related('produto').all()
    serializer_class = AdicionalSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        return [IsAdmin()]


@api_view(['GET'])
@permission_classes([AllowAny])
def cardapio(request):
    """
    RF05 — Retorna o cardápio completo organizado por categorias,
    com produtos e adicionais.
    """
    categorias = Categoria.objects.prefetch_related(
        'produtos__adicionais',
    ).all()
    serializer = CategoriaComProdutosSerializer(categorias, many=True)
    return Response(serializer.data)


# ============================================================
# Mesa e QR Code (RF01–RF04)
# ============================================================
class MesaViewSet(viewsets.ModelViewSet):
    """CRUD de mesas. Admin gerencia; garçom pode ver."""
    queryset = Mesa.objects.all()
    serializer_class = MesaSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsEquipe()]
        return [IsAdmin()]

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def gerar_qrcode(self, request, pk=None):
        """RF02 — Gera o QR Code da mesa com URL baseada no UUID."""
        mesa = self.get_object()
        # URL que o QR Code vai apontar (ajustar conforme o deploy)
        base_url = request.build_absolute_uri('/').rstrip('/')
        url = f"{base_url}/mesa/{mesa.token_uuid}/"

        # Gera o QR Code
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')

        # Salva como imagem
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        filename = f"mesa_{mesa.numero}_qrcode.png"
        mesa.qr_code.save(filename, ContentFile(buffer.read()), save=True)

        return Response({
            'mensagem': f'QR Code gerado para Mesa {mesa.numero}',
            'qr_code_url': request.build_absolute_uri(mesa.qr_code.url),
            'mesa_url': url,
        })


@api_view(['GET'])
@permission_classes([AllowAny])
def mesa_por_uuid(request, uuid):
    """
    RF01 — Acessada pelo QR Code. Retorna os dados da mesa pelo UUID.
    Não requer login (cliente acessa).
    """
    mesa = get_object_or_404(Mesa, token_uuid=uuid, ativa=True)
    sessao = mesa.sessao_ativa

    data = MesaClienteSerializer(mesa).data
    data['sessao_ativa'] = sessao is not None
    data['sessao_id'] = sessao.id if sessao else None

    return Response(data)


# ============================================================
# Sessão da Mesa (RF03, RN04, RN05)
# ============================================================
class SessaoMesaViewSet(viewsets.ReadOnlyModelViewSet):
    """Listagem de sessões. Garçom ou Admin."""
    queryset = SessaoMesa.objects.select_related('mesa', 'aberta_por').all()
    serializer_class = SessaoMesaSerializer
    permission_classes = [IsGarcomOuAdmin]


@api_view(['POST'])
@permission_classes([IsGarcomOuAdmin])
def abrir_sessao(request, mesa_id):
    """RF03 — Garçom abre a sessão de uma mesa."""
    try:
        with transaction.atomic():
            mesa = get_object_or_404(
                Mesa.objects.select_for_update(), id=mesa_id, ativa=True,
            )
            # RN05 — A restrição no banco protege também gravações concorrentes.
            if mesa.sessao_ativa:
                return Response(
                    {'erro': f'Mesa {mesa.numero} já possui uma sessão aberta.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            sessao = SessaoMesa.objects.create(mesa=mesa, aberta_por=request.user)
    except IntegrityError:
        if not SessaoMesa.objects.filter(mesa_id=mesa_id, ativa=True).exists():
            raise
        return Response(
            {'erro': f'Mesa {mesa.numero} já possui uma sessão aberta.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        SessaoMesaSerializer(sessao).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
@permission_classes([IsGarcomOuAdmin])
@transaction.atomic
def fechar_sessao(request, sessao_id):
    """RF03 — Garçom fecha a sessão. Só se todos os pedidos estiverem entregues ou cancelados."""
    sessao = get_object_or_404(SessaoMesa.objects.select_for_update(), id=sessao_id, ativa=True)

    # RN09 — Verifica se todos os pedidos estão entregues ou cancelados
    pedidos_pendentes = sessao.pedidos.exclude(
        status__in=['ENTREGUE', 'CANCELADO']
    ).exists()

    if pedidos_pendentes:
        return Response(
            {'erro': 'Não é possível fechar a sessão. Há pedidos que ainda não foram entregues ou cancelados.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Verifica se a conta foi paga
    conta = getattr(sessao, 'conta', None)
    total = sum(p.valor_total for p in sessao.pedidos.exclude(status='CANCELADO'))
    if total > 0 and (not conta or not conta.pago):
        return Response(
            {'erro': 'A conta ainda não foi paga.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    sessao.ativa = False
    sessao.fechada_em = timezone.now()
    sessao.save()

    return Response(
        {'mensagem': f'Sessão da Mesa {sessao.mesa.numero} encerrada com sucesso.'},
    )


# ============================================================
# Pedido — Criação e Fluxo (RF08–RF12, RN01–RN08)
# ============================================================
@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def criar_pedido(request):
    """
    RF08–RF11 — Cliente envia um pedido com itens e adicionais.
    Recebe mesa_uuid, observacao e lista de itens.
    """
    serializer = PedidoCriarSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    dados = serializer.validated_data
    mesa_uuid = dados['mesa_uuid']

    # Busca a mesa
    mesa = get_object_or_404(Mesa, token_uuid=mesa_uuid, ativa=True)

    # RN04 — Só é possível enviar pedido para uma mesa com sessão aberta
    sessao = SessaoMesa.objects.select_for_update().filter(mesa=mesa, ativa=True).first()
    if not sessao:
        return Response(
            {'erro': 'Esta mesa não possui uma sessão aberta. Peça ao garçom para abrir.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # RN10 — Sessão encerrada não aceita novos pedidos
    if not sessao.ativa:
        return Response(
            {'erro': 'A sessão desta mesa foi encerrada.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        # Cria o pedido
        pedido = Pedido.objects.create(
            sessao=sessao,
            observacao=dados.get('observacao', ''),
        )

        # Registra status inicial (RN03)
        HistoricoStatusPedido.objects.create(
            pedido=pedido,
            status_anterior='',
            status_novo='RECEBIDO',
            alterado_por=request.user if request.user.is_authenticated else None,
        )

        # Processa cada item
        for item_data in dados['itens']:
            produto = get_object_or_404(Produto.objects.select_for_update(), id=item_data['produto_id'])

            # RN08 — Produto indisponível não pode entrar no pedido
            if not produto.disponivel:
                raise serializers.ValidationError(
                    f'O produto "{produto.nome}" está indisponível.'
                )

            # Grava o preço do produto no momento do pedido (RNF08)
            item_pedido = ItemPedido.objects.create(
                pedido=pedido,
                produto=produto,
                quantidade=item_data['quantidade'],
                preco_unitario=produto.preco,
                observacao=item_data.get('observacao', ''),
            )

            # Processa adicionais
            for adicional_id in item_data.get('adicionais_ids', []):
                adicional = get_object_or_404(
                    Adicional,
                    id=adicional_id,
                    produto=produto,
                )
                # Grava o preço do adicional no momento do pedido (RNF08)
                ItemPedidoAdicional.objects.create(
                    item_pedido=item_pedido,
                    adicional=adicional,
                    preco=adicional.preco,
                )

    # Retorna o pedido criado
    pedido.refresh_from_db()
    return Response(
        PedidoSerializer(pedido).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(['PATCH'])
@permission_classes([IsEquipe])
@transaction.atomic
def alterar_status_pedido(request, pedido_id):
    """
    RN01 — Altera o status do pedido respeitando a sequência válida.
    RN02 — Cancelamento só antes de entrar em preparação.
    RN03 — Registra a mudança com data, hora e quem a fez.
    """
    pedido = get_object_or_404(Pedido.objects.select_for_update(), id=pedido_id)
    serializer = PedidoStatusSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    novo_status = serializer.validated_data['status']

    # RN01 — Verifica se a transição é válida
    if not pedido.pode_transitar_para(novo_status):
        return Response(
            {
                'erro': (
                    f'Transição inválida: {pedido.get_status_display()} → '
                    f'{dict(Pedido.STATUS_CHOICES).get(novo_status, novo_status)}. '
                    f'Transições permitidas: {pedido.TRANSICOES_VALIDAS.get(pedido.status, [])}'
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    papel = request.user.perfil.role
    acoes = {
        'COZINHA': {'EM_PREPARACAO', 'PRONTO', 'CANCELADO'},
        'GARCOM': {'A_CAMINHO', 'ENTREGUE', 'CANCELADO'},
    }
    if papel != 'ADMIN' and novo_status not in acoes.get(papel, set()):
        return Response({'erro': 'Seu perfil não pode executar esta etapa.'}, status=403)

    # RN02 — Cancelamento só antes do preparo
    if novo_status == 'CANCELADO' and not pedido.pode_cancelar():
        return Response(
            {'erro': 'Este pedido só poderia ser cancelado antes de entrar em preparação.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    status_anterior = pedido.status
    pedido.status = novo_status
    pedido.save()

    # RN03 — Registra auditoria
    HistoricoStatusPedido.objects.create(
        pedido=pedido,
        status_anterior=status_anterior,
        status_novo=novo_status,
        alterado_por=request.user if request.user.is_authenticated else None,
    )

    return Response(PedidoSerializer(pedido).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def pedidos_da_mesa(request, uuid):
    """RF12 — Cliente acompanha os pedidos da mesa pela UUID."""
    mesa = get_object_or_404(Mesa, token_uuid=uuid, ativa=True)
    sessao = mesa.sessao_ativa

    if not sessao:
        return Response({'pedidos': [], 'mensagem': 'Nenhuma sessão ativa.'})

    pedidos = sessao.pedidos.prefetch_related(
        'itens__produto',
        'itens__itens_adicionais__adicional',
    ).all()

    return Response(PedidoSerializer(pedidos, many=True).data)


# ============================================================
# Painel da Cozinha (RF13–RF16)
# ============================================================
@api_view(['GET'])
@permission_classes([IsCozinhaOuAdmin])
def painel_cozinha(request):
    """
    RF13 — Pedidos agrupados por status para a cozinha.
    Mostra RECEBIDO, EM_PREPARACAO e PRONTO.
    """
    status_cozinha = ['RECEBIDO', 'EM_PREPARACAO', 'PRONTO']

    pedidos = Pedido.objects.filter(
        status__in=status_cozinha,
    ).select_related(
        'sessao__mesa',
    ).prefetch_related(
        'itens__produto',
        'itens__itens_adicionais__adicional',
    ).order_by('created_at', 'id')

    resultado = {s: [] for s in status_cozinha}
    for pedido in PedidoCozinhaSerializer(pedidos, many=True).data:
        resultado[pedido['status']].append(pedido)

    return Response(resultado)


@api_view(['PATCH'])
@permission_classes([IsCozinhaOuAdmin])
def marcar_disponibilidade_produto(request, produto_id):
    """RF15 — A cozinha pode marcar um produto como indisponível."""
    produto = get_object_or_404(Produto, id=produto_id)
    serializer = ProdutoDisponibilidadeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    produto.disponivel = serializer.validated_data['disponivel']
    produto.save(update_fields=['disponivel'])

    return Response(ProdutoSerializer(produto).data)


# ============================================================
# Painel do Garçom (RF17–RF18)
# ============================================================
@api_view(['GET'])
@permission_classes([IsGarcomOuAdmin])
def painel_garcom(request):
    """
    RF17 — Pedidos prontos e a caminho para o garçom.
    RF18 — Mesas que pediram a conta.
    """
    # Pedidos prontos e a caminho
    pedidos_prontos = Pedido.objects.filter(
        status__in=['PRONTO', 'A_CAMINHO'],
    ).select_related(
        'sessao__mesa',
    ).prefetch_related(
        'itens__produto',
        'itens__itens_adicionais__adicional',
    ).order_by('created_at')

    # Mesas aguardando conta
    mesas_aguardando = Mesa.objects.filter(
        sessoes__ativa=True,
        sessoes__conta_solicitada=True,
    ).distinct()

    return Response({
        'pedidos_prontos': PedidoSerializer(pedidos_prontos, many=True).data,
        'mesas_aguardando_conta': MesaSerializer(mesas_aguardando, many=True).data,
    })


@api_view(['GET'])
@permission_classes([IsGarcomOuAdmin])
def mapa_mesas(request):
    """RF04 — Situação de cada mesa (livre, ocupada, aguardando conta)."""
    mesas = Mesa.objects.filter(ativa=True).prefetch_related('sessoes')
    return Response(MesaSerializer(mesas, many=True).data)


# ============================================================
# Conta e Pagamento Simulado (RF19–RF22, RN09–RN10)
# ============================================================
@api_view(['GET'])
@permission_classes([AllowAny])
def ver_conta(request, uuid):
    """RF19 — Cliente vê a conta da mesa com todos os pedidos."""
    mesa = get_object_or_404(Mesa, token_uuid=uuid, ativa=True)
    sessao = mesa.sessao_ativa

    if not sessao:
        return Response(
            {'erro': 'Nenhuma sessão ativa nesta mesa.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    pedidos = sessao.pedidos.exclude(
        status='CANCELADO',
    ).prefetch_related(
        'itens__produto',
        'itens__itens_adicionais__adicional',
    )

    total = sum(p.valor_total for p in pedidos)

    return Response({
        'mesa': MesaClienteSerializer(mesa).data,
        'sessao_id': sessao.id,
        'pedidos': PedidoSerializer(pedidos, many=True).data,
        'valor_total': str(total),
        'conta_solicitada': sessao.conta_solicitada,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def solicitar_conta(request, uuid):
    """RF20 — Cliente ou garçom solicita o fechamento da conta."""
    mesa = get_object_or_404(Mesa, token_uuid=uuid, ativa=True)
    sessao = mesa.sessao_ativa

    if not sessao:
        return Response(
            {'erro': 'Nenhuma sessão ativa nesta mesa.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    sessao.conta_solicitada = True
    sessao.save()

    return Response({'mensagem': 'Conta solicitada com sucesso.'})


@api_view(['POST'])
@permission_classes([IsGarcomOuAdmin])
@transaction.atomic
def processar_pagamento(request, sessao_id):
    """
    RF21–RF22 — Pagamento simulado.
    RN09 — Só pode fechar se todos entregues ou cancelados.
    """
    sessao = get_object_or_404(SessaoMesa.objects.select_for_update(), id=sessao_id, ativa=True)

    serializer = PagamentoSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # RN09 — Verifica se todos os pedidos estão entregues ou cancelados
    pedidos_pendentes = sessao.pedidos.exclude(
        status__in=['ENTREGUE', 'CANCELADO']
    ).exists()

    if pedidos_pendentes:
        return Response(
            {'erro': 'Todos os pedidos devem estar entregues ou cancelados para fechar a conta.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        # Cria ou atualiza a conta
        conta, _ = Conta.objects.get_or_create(sessao=sessao)
        conta.calcular_total()
        conta.meio_pagamento = serializer.validated_data['meio_pagamento']
        conta.pago = True
        conta.pago_em = timezone.now()
        conta.save()

        # RF22 — Encerra a sessão e a mesa volta a ficar livre
        sessao.ativa = False
        sessao.fechada_em = timezone.now()
        sessao.conta_solicitada = False
        sessao.save()

    return Response({
        'mensagem': 'Pagamento aprovado! Sessão encerrada.',
        'conta': ContaSerializer(conta).data,
    })


# ============================================================
# Administração (RF24–RF25)
# ============================================================
@api_view(['GET'])
@permission_classes([IsAdmin])
def consultar_pedidos(request):
    """RF25 — Consulta de pedidos com filtros por data."""
    pedidos = Pedido.objects.select_related(
        'sessao__mesa',
    ).prefetch_related(
        'itens__produto',
        'itens__itens_adicionais__adicional',
    )

    # Filtros por data
    data_inicio = request.query_params.get('data_inicio')
    data_fim = request.query_params.get('data_fim')
    status_filtro = request.query_params.get('status')

    if data_inicio:
        pedidos = pedidos.filter(created_at__date__gte=data_inicio)
    if data_fim:
        pedidos = pedidos.filter(created_at__date__lte=data_fim)
    if status_filtro:
        pedidos = pedidos.filter(status=status_filtro)

    return Response(PedidoSerializer(pedidos, many=True).data)


@api_view(['GET'])
@permission_classes([IsAdmin])
def consultar_contas(request):
    """RF25 — Consulta de contas fechadas com filtros por data."""
    contas = Conta.objects.select_related('sessao__mesa')

    data_inicio = request.query_params.get('data_inicio')
    data_fim = request.query_params.get('data_fim')

    if data_inicio:
        contas = contas.filter(criado_em__date__gte=data_inicio)
    if data_fim:
        contas = contas.filter(criado_em__date__lte=data_fim)

    return Response(ContaSerializer(contas, many=True).data)


# ============================================================
# Autenticação simples
# ============================================================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def usuario_atual(request):
    """Retorna dados do usuário logado e seu perfil."""
    user = request.user
    perfil = getattr(user, 'perfil', None)

    data = {
        'id': user.id,
        'username': user.username,
        'nome': user.get_full_name(),
        'is_staff': user.is_staff,
    }

    if perfil:
        data['perfil'] = PerfilSerializer(perfil).data

    return Response(data)
