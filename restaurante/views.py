from drf_spectacular.utils import extend_schema, OpenApiParameter
from .api_schema import (
    ERROS, FILTROS, ContaMesaSerializer, CozinhaSerializer, GarcomSerializer,
    MensagemSerializer, MesaContextoSerializer, PagamentoResultadoSerializer,
    QrLinksSerializer, UsuarioSerializer,
)
from django.conf import settings
from django.urls import reverse
from django.db.models.deletion import ProtectedError
from . import services
from .security import vincular_mesa, validar_mesa, equipe_mesa, chave_comanda, comanda_cliente, comandas_acessiveis, guardar_comanda, visao_equipe
from .serializers import FiltroDatasSerializer
from decimal import Decimal

from django.shortcuts import get_object_or_404
from django.db import transaction

from rest_framework import viewsets, status, serializers
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import (
    Mesa, SessaoMesa, Categoria, Produto, Adicional, Pedido, Conta,
)
from .serializers import (
    PerfilSerializer,
    MesaSerializer, MesaClienteSerializer,
    SessaoMesaSerializer,
    CategoriaSerializer, CategoriaComProdutosSerializer,
    ProdutoSerializer, AdicionalSerializer,
    PedidoSerializer, PedidoCriarSerializer, PedidoStatusSerializer,
    PedidoCozinhaSerializer, ProdutoDisponibilidadeSerializer,
    ContaSerializer, PagamentoSerializer,
)
from .permissions import IsAdmin, IsEquipe, IsCozinhaOuAdmin, IsGarcomOuAdmin, PodeCriarPedido


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


@extend_schema(request=None, responses={200: CategoriaComProdutosSerializer(many=True)})
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
    queryset = Mesa.objects.com_sessao_ativa()
    serializer_class = MesaSerializer

    @transaction.atomic
    def perform_update(self, serializer):
        serializer.instance = get_object_or_404(Mesa.objects.select_for_update(), pk=serializer.instance.pk)
        if serializer.validated_data.get('ativa') is False and serializer.instance.sessao_ativa:
            raise serializers.ValidationError('Encerre a sessão antes de desativar a mesa.')
        serializer.save()

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsEquipe()]
        return [IsAdmin()]

    @extend_schema(request=None, responses={200: QrLinksSerializer, **ERROS})
    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def gerar_qrcode(self, request, pk=None):
        """RF02 — Gera o QR Code da mesa com URL baseada no UUID."""
        mesa = self.get_object()
        return Response({
            'qr_code_url': request.build_absolute_uri(reverse('qr-download', args=[mesa.pk])),
            'mesa_url': settings.PUBLIC_BASE_URL + reverse('cliente', args=[mesa.token_uuid]),
        })



@extend_schema(request=None, responses={200: MesaContextoSerializer, **ERROS})
@api_view(['GET'])
@permission_classes([AllowAny])
def mesa_por_uuid(request, uuid):
    """
    RF01 — Acessada pelo QR Code. Retorna os dados da mesa pelo UUID.
    Não requer login (cliente acessa).
    """
    mesa = get_object_or_404(Mesa, token_uuid=uuid, ativa=True)
    equipe = visao_equipe(request)
    sessao = mesa.sessao_ativa if equipe else comanda_cliente(request, mesa)

    data = MesaClienteSerializer(mesa).data
    data['sessao_ativa'] = bool(sessao and sessao.ativa)
    acesso = equipe or bool(chave_comanda(request, mesa)) and (not sessao or sessao.ativa)
    data['acesso_liberado'] = acesso
    data['atendimento_id'] = chave_comanda(request, mesa) if acesso and not equipe else None
    data['sessao_id'] = sessao.id if sessao and sessao.ativa and acesso else None
    data['atendimento_encerrado'] = bool(not equipe and sessao and not sessao.ativa)
    data['comandas'] = [] if equipe else list(comandas_acessiveis(request, mesa).values('id', 'conta_solicitada'))

    return Response(data)


@extend_schema(request=None, responses={200: MensagemSerializer, **ERROS})
@api_view(['POST'])
@permission_classes([AllowAny])
def novo_atendimento(request, uuid):
    mesa = get_object_or_404(Mesa, token_uuid=uuid, ativa=True)
    vincular_mesa(request, mesa, novo=True)
    return Response({'mensagem': 'Novo atendimento iniciado. Escolha e confirme seu pedido.'})


# ============================================================
# Sessão da Mesa (RF03, RN04, RN05)
# ============================================================
class SessaoMesaViewSet(viewsets.ReadOnlyModelViewSet):
    """Listagem de sessões. Garçom ou Admin."""
    queryset = SessaoMesa.objects.select_related('mesa', 'aberta_por').all()
    serializer_class = SessaoMesaSerializer
    permission_classes = [IsGarcomOuAdmin]

    @extend_schema(responses={200: ContaMesaSerializer, **ERROS})
    @action(detail=True, methods=['get'])
    @transaction.atomic
    def conta(self, request, pk=None):
        sessao = services.sessao_bloqueada(self.get_object().pk)
        pedidos = sessao.pedidos.para_exibicao()
        return Response({
            'mesa': MesaClienteSerializer(sessao.mesa).data, 'sessao_id': sessao.pk,
            'pedidos': PedidoSerializer(pedidos, many=True).data,
            'valor_total': str(sum((p.valor_total for p in pedidos if p.status != 'CANCELADO'), Decimal('0.00'))),
            'conta_solicitada': sessao.conta_solicitada,
            'versao_conta': sessao.versao_conta,
        })

    @extend_schema(request=None, responses={200: MensagemSerializer, **ERROS})
    @action(detail=True, methods=['post'], url_path='solicitar-conta')
    def solicitar_conta(self, request, pk=None):
        sessao = self.get_object()
        services.pedir_conta(sessao.mesa.token_uuid, sessao.pk)
        return Response({'mensagem': 'Conta solicitada.'})

    @extend_schema(request=None, responses={200: MensagemSerializer, **ERROS})
    @action(detail=True, methods=['post'])
    def retomar(self, request, pk=None):
        services.retomar(self.get_object().pk, request.user)
        return Response({'mensagem': 'Atendimento retomado. Novos pedidos estão liberados.'})


@extend_schema(request=None, responses={201: SessaoMesaSerializer, **ERROS})
@api_view(['POST'])
@permission_classes([IsGarcomOuAdmin])
def abrir_sessao(request, mesa_id):
    return Response(SessaoMesaSerializer(services.abrir(mesa_id, request.user)).data, status=201)


@extend_schema(request=None, responses={200: MensagemSerializer, **ERROS})
@api_view(['POST'])
@permission_classes([IsGarcomOuAdmin])
@transaction.atomic
def fechar_sessao(request, sessao_id):
    services.fechar(sessao_id, request.user)
    return Response({'mensagem': 'Sessão encerrada com sucesso.'})


# ============================================================
# Pedido — Criação e Fluxo (RF08–RF12, RN01–RN08)
# ============================================================
@extend_schema(request=PedidoCriarSerializer, responses={201: PedidoSerializer, **ERROS})
@api_view(['POST'])
@permission_classes([PodeCriarPedido])
@transaction.atomic
def criar_pedido(request):
    serializer = PedidoCriarSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    dados = serializer.validated_data
    mesa = get_object_or_404(Mesa, token_uuid=dados['mesa_uuid'], ativa=True)
    validar_mesa(request, mesa, dados.get('sessao_id'))
    geracao = chave_comanda(request, mesa)
    pedido = services.criar(dados, request.user, geracao=geracao)
    return Response(PedidoSerializer(pedido).data, status=201)


@extend_schema(request=PedidoStatusSerializer, responses={200: PedidoSerializer, **ERROS})
@api_view(['PATCH'])
@permission_classes([IsEquipe])
@transaction.atomic
def alterar_status_pedido(request, pedido_id):
    serializer = PedidoStatusSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    pedido = services.transitar(pedido_id, serializer.validated_data['status'], request.user)
    return Response(PedidoSerializer(pedido).data)


@extend_schema(request=None, responses={200: PedidoSerializer(many=True), **ERROS})
@api_view(['GET'])
@permission_classes([AllowAny])
def pedidos_da_mesa(request, uuid):
    """RF12 — Cliente acompanha os pedidos da mesa pela UUID."""
    mesa = get_object_or_404(Mesa, token_uuid=uuid, ativa=True)
    equipe = visao_equipe(request)
    sessao = mesa.sessao_ativa if equipe else validar_mesa(request, mesa)

    if not sessao:
        return Response([])

    pedidos = Pedido.objects.filter(sessao__mesa=mesa, sessao__ativa=True).para_exibicao() if equipe else sessao.pedidos.para_exibicao()

    return Response(PedidoSerializer(pedidos, many=True).data)


# ============================================================
# Painel da Cozinha (RF13–RF16)
# ============================================================
@extend_schema(request=None, responses={200: CozinhaSerializer, **ERROS})
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
    ).para_exibicao().order_by('created_at', 'id')

    resultado = {s: [] for s in status_cozinha}
    for pedido in PedidoCozinhaSerializer(pedidos, many=True).data:
        resultado[pedido['status']].append(pedido)

    return Response(resultado)


@extend_schema(request=ProdutoDisponibilidadeSerializer, responses={200: ProdutoSerializer, **ERROS})
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
@extend_schema(request=None, responses={200: GarcomSerializer, **ERROS})
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
    ).para_exibicao().order_by('created_at')

    # Mesas aguardando conta
    mesas_aguardando = Mesa.objects.filter(
        sessoes__ativa=True,
        sessoes__conta_solicitada=True,
    ).distinct().com_sessao_ativa()

    return Response({
        'pedidos_prontos': PedidoSerializer(pedidos_prontos, many=True).data,
        'mesas_aguardando_conta': MesaSerializer(mesas_aguardando, many=True, context={'request': request}).data,
        'comandas_aguardando_conta': SessaoMesaSerializer(SessaoMesa.objects.filter(ativa=True, conta_solicitada=True).select_related('mesa'), many=True).data,
    })


@extend_schema(request=None, responses={200: MesaSerializer(many=True), **ERROS})
@api_view(['GET'])
@permission_classes([IsGarcomOuAdmin])
def mapa_mesas(request):
    """RF04 — Situação de cada mesa (livre, ocupada, aguardando conta)."""
    mesas = Mesa.objects.filter(ativa=True).com_sessao_ativa()
    return Response(MesaSerializer(mesas, many=True, context={'request': request}).data)


# ============================================================
# Conta e Pagamento Simulado (RF19–RF22, RN09–RN10)
# ============================================================
@extend_schema(request=None, responses={200: ContaMesaSerializer, **ERROS})
@api_view(['GET'])
@permission_classes([AllowAny])
def ver_conta(request, uuid):
    """RF19 — Cliente vê a conta da mesa com todos os pedidos."""
    mesa = get_object_or_404(Mesa, token_uuid=uuid, ativa=True)
    equipe = visao_equipe(request)
    sessao = mesa.sessao_ativa if equipe else validar_mesa(request, mesa)

    if not sessao:
        return Response(
            {'erro': 'Nenhuma sessão ativa nesta mesa.'},
            status=status.HTTP_404_NOT_FOUND,
        )

    pedidos = Pedido.objects.filter(sessao__mesa=mesa, sessao__ativa=True).para_exibicao() if equipe else sessao.pedidos.para_exibicao()

    total = sum((p.valor_total for p in pedidos if p.status != 'CANCELADO'), Decimal('0.00'))

    return Response({
        'mesa': MesaClienteSerializer(mesa).data,
        'sessao_id': None if equipe else sessao.id,
        'pedidos': PedidoSerializer(pedidos, many=True).data,
        'valor_total': str(total),
        'conta_solicitada': mesa.sessoes.filter(ativa=True, conta_solicitada=True).exists() if equipe else sessao.conta_solicitada,
        'versao_conta': sessao.versao_conta,
    })


@extend_schema(request=None, responses={200: MensagemSerializer, **ERROS})
@api_view(['POST'])
@permission_classes([AllowAny])
def solicitar_conta(request, uuid):
    mesa = get_object_or_404(Mesa, token_uuid=uuid, ativa=True)
    sessao = validar_mesa(request, mesa)
    if not sessao:
        return Response({'erro': 'Nenhuma sessão ativa nesta mesa.'}, status=404)
    services.pedir_conta(uuid, sessao.pk)
    return Response({'mensagem': 'Conta solicitada com sucesso.'})


@extend_schema(request=PagamentoSerializer, responses={200: PagamentoResultadoSerializer, **ERROS})
@api_view(['POST'])
@permission_classes([IsGarcomOuAdmin])
@transaction.atomic
def processar_pagamento(request, sessao_id):
    serializer = PagamentoSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    dados = serializer.validated_data
    conta = services.pagar(sessao_id, dados['meio_pagamento'], request.user,
        total_esperado=dados['total_esperado'], versao_conta=dados['versao_conta'])
    return Response({'mensagem': 'Pagamento aprovado! Sessão encerrada.', 'conta': ContaSerializer(conta).data})


# ============================================================
# Administração (RF24–RF25)
# ============================================================
@extend_schema(request=None, parameters=FILTROS + [OpenApiParameter('status', str, enum=[s[0] for s in Pedido.STATUS_CHOICES])], responses={200: PedidoSerializer(many=True), **ERROS})
@api_view(['GET'])
@permission_classes([IsAdmin])
def consultar_pedidos(request):
    """RF25 — Consulta de pedidos com filtros por data."""
    pedidos = Pedido.objects.para_exibicao()

    # Filtros por data
    filtros = FiltroDatasSerializer(data=request.query_params)
    filtros.is_valid(raise_exception=True)
    data_inicio = filtros.validated_data.get('data_inicio')
    data_fim = filtros.validated_data.get('data_fim')
    status_filtro = filtros.validated_data.get('status')

    if data_inicio:
        pedidos = pedidos.filter(created_at__date__gte=data_inicio)
    if data_fim:
        pedidos = pedidos.filter(created_at__date__lte=data_fim)
    if status_filtro:
        pedidos = pedidos.filter(status=status_filtro)

    return Response(PedidoSerializer(pedidos, many=True).data)


@extend_schema(request=None, parameters=FILTROS, responses={200: ContaSerializer(many=True), **ERROS})
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
@extend_schema(request=None, responses={200: UsuarioSerializer, **ERROS})
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
