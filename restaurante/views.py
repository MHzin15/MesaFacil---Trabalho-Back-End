from django.conf import settings
from django.urls import reverse
from django.db.models.deletion import ProtectedError
from . import services
from .security import vincular_mesa, validar_mesa
from .serializers import FiltroDatasSerializer
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
class CatalogoViewSet(viewsets.ModelViewSet):
    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise serializers.ValidationError({'erro': 'Cadastro utilizado em histórico; não pode ser excluído.'})


class CategoriaViewSet(CatalogoViewSet):
    """CRUD de categorias. Leitura pública, escrita para Admin."""
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        return [IsAdmin()]


class ProdutoViewSet(CatalogoViewSet):
    """CRUD de produtos. Leitura pública, escrita para Admin."""
    queryset = Produto.objects.select_related('categoria').prefetch_related('adicionais').all()
    serializer_class = ProdutoSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        return [IsAdmin()]


class AdicionalViewSet(CatalogoViewSet):
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
        return Response({
            'qr_code_url': request.build_absolute_uri(reverse('qr-download', args=[mesa.pk])),
            'mesa_url': settings.PUBLIC_BASE_URL + reverse('cliente', args=[mesa.token_uuid]),
        })



@api_view(['GET'])
@permission_classes([AllowAny])
def mesa_por_uuid(request, uuid):
    """
    RF01 — Acessada pelo QR Code. Retorna os dados da mesa pelo UUID.
    Não requer login (cliente acessa).
    """
    mesa = get_object_or_404(Mesa, token_uuid=uuid, ativa=True)
    sessao = vincular_mesa(request, mesa)

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
    return Response(SessaoMesaSerializer(services.abrir(mesa_id, request.user)).data, status=201)


@api_view(['POST'])
@permission_classes([IsGarcomOuAdmin])
@transaction.atomic
def fechar_sessao(request, sessao_id):
    services.fechar(sessao_id, request.user)
    return Response({'mensagem': 'Sessão encerrada com sucesso.'})


# ============================================================
# Pedido — Criação e Fluxo (RF08–RF12, RN01–RN08)
# ============================================================
@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def criar_pedido(request):
    serializer = PedidoCriarSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    dados = serializer.validated_data
    mesa = get_object_or_404(Mesa, token_uuid=dados['mesa_uuid'], ativa=True)
    # Sem sessão aberta, a regra de negócio retorna um erro claro antes do contexto.
    if mesa.sessao_ativa:
        validar_mesa(request, mesa, dados.get('sessao_id'))
    pedido = services.criar(dados, request.user)
    return Response(PedidoSerializer(pedido).data, status=201)


@api_view(['PATCH'])
@permission_classes([IsEquipe])
@transaction.atomic
def alterar_status_pedido(request, pedido_id):
    serializer = PedidoStatusSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    pedido = services.transitar(pedido_id, serializer.validated_data['status'], request.user)
    return Response(PedidoSerializer(pedido).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def pedidos_da_mesa(request, uuid):
    """RF12 — Cliente acompanha os pedidos da mesa pela UUID."""
    mesa = get_object_or_404(Mesa, token_uuid=uuid, ativa=True)
    sessao = validar_mesa(request, mesa)

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
    sessao = validar_mesa(request, mesa)

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
    mesa = get_object_or_404(Mesa, token_uuid=uuid, ativa=True)
    sessao = validar_mesa(request, mesa)
    if not sessao:
        return Response({'erro': 'Nenhuma sessão ativa nesta mesa.'}, status=404)
    services.pedir_conta(uuid, sessao.pk)
    return Response({'mensagem': 'Conta solicitada com sucesso.'})


@api_view(['POST'])
@permission_classes([IsGarcomOuAdmin])
@transaction.atomic
def processar_pagamento(request, sessao_id):
    serializer = PagamentoSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    conta = services.pagar(sessao_id, serializer.validated_data['meio_pagamento'], request.user)
    return Response({'mensagem': 'Pagamento aprovado! Sessão encerrada.', 'conta': ContaSerializer(conta).data})


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
    filtros = FiltroDatasSerializer(data=request.query_params)
    filtros.is_valid(raise_exception=True)
    data_inicio = filtros.validated_data.get('data_inicio')
    data_fim = filtros.validated_data.get('data_fim')
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
    contas = Conta.objects.filter(pago=True).select_related('sessao__mesa')

    filtros = FiltroDatasSerializer(data=request.query_params)
    filtros.is_valid(raise_exception=True)
    data_inicio = filtros.validated_data.get('data_inicio')
    data_fim = filtros.validated_data.get('data_fim')

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
