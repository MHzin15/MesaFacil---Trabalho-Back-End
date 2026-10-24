"""Regras transacionais compartilhadas pela API e pelo admin."""
from decimal import Decimal
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from restaurante.models import (
    Mesa, SessaoMesa, Produto, Adicional, Pedido, ItemPedido,
    ItemPedidoAdicional, HistoricoStatusPedido, Conta,
)


def erro(message):
    raise ValidationError({'erro': message})


def papel(user, roles):
    profile = getattr(user, 'perfil', None)
    if not user.is_authenticated or not profile or profile.role not in roles:
        raise PermissionDenied('Seu perfil não pode executar esta ação.')


def sessao_bloqueada(sessao_id):
    ref = get_object_or_404(SessaoMesa, pk=sessao_id)
    get_object_or_404(Mesa.objects.select_for_update(), pk=ref.mesa_id)
    return get_object_or_404(SessaoMesa.objects.select_for_update(), pk=sessao_id)


def abrir(mesa_id, user):
    papel(user, ('ADMIN', 'GARCOM'))
    try:
        with transaction.atomic():
            mesa = get_object_or_404(Mesa.objects.select_for_update(), pk=mesa_id, ativa=True)
            if mesa.sessao_ativa:
                erro(f'Mesa {mesa.numero} já possui uma sessão aberta.')
            return SessaoMesa.objects.create(mesa=mesa, aberta_por=user)
    except IntegrityError:
        if SessaoMesa.objects.filter(mesa_id=mesa_id, ativa=True).exists():
            erro('Esta mesa já possui uma sessão aberta.')
        raise


@transaction.atomic
def criar(dados, user):
    mesa = get_object_or_404(Mesa.objects.select_for_update(), token_uuid=dados['mesa_uuid'], ativa=True)
    sessao = SessaoMesa.objects.select_for_update().filter(mesa=mesa, ativa=True).first()
    if not sessao:
        erro('Esta mesa não possui uma sessão aberta. Peça ao garçom para abrir.')
    if dados.get('sessao_id') != sessao.pk:
        erro('A sessão mudou ou foi encerrada. Atualize a mesa e revise o pedido.')
    products = {p.pk: p for p in Produto.objects.select_for_update().filter(
        pk__in=[i['produto_id'] for i in dados['itens']]).order_by('pk')}
    addons = {a.pk: a for a in Adicional.objects.select_for_update().filter(
        pk__in=[a for i in dados['itens'] for a in i.get('adicionais_ids', [])]).order_by('pk')}
    pedido = Pedido.objects.create(sessao=sessao, observacao=dados.get('observacao', ''))
    HistoricoStatusPedido.objects.create(pedido=pedido, status_novo='RECEBIDO',
        alterado_por=user if user.is_authenticated else None)
    for item in dados['itens']:
        produto = products.get(item['produto_id'])
        if not produto:
            get_object_or_404(Produto, pk=item['produto_id'])
        if not produto.disponivel:
            erro(f'O produto "{produto.nome}" está indisponível.')
        saved = ItemPedido.objects.create(pedido=pedido, produto=produto,
            quantidade=item['quantidade'], preco_unitario=produto.preco, observacao=item.get('observacao', ''))
        for aid in item.get('adicionais_ids', []):
            adicional = addons.get(aid)
            if not adicional or adicional.produto_id != produto.pk:
                from django.http import Http404
                raise Http404('Adicional não pertence ao produto.')
            ItemPedidoAdicional.objects.create(item_pedido=saved, adicional=adicional, preco=adicional.preco)
    return pedido


@transaction.atomic
def transitar(pedido_id, novo, user):
    papel(user, ('ADMIN', 'COZINHA', 'GARCOM'))
    ref = get_object_or_404(Pedido, pk=pedido_id)
    sessao = sessao_bloqueada(ref.sessao_id)
    pedido = get_object_or_404(Pedido.objects.select_for_update(), pk=pedido_id)
    if not sessao.ativa:
        erro('A sessão foi encerrada.')
    if not pedido.pode_transitar_para(novo):
        erro('Transição inválida. Não é permitido pular, repetir ou voltar etapas.')
    allowed = {'COZINHA': {'EM_PREPARACAO', 'PRONTO', 'CANCELADO'},
               'GARCOM': {'A_CAMINHO', 'ENTREGUE', 'CANCELADO'}}
    if user.perfil.role != 'ADMIN' and novo not in allowed[user.perfil.role]:
        raise PermissionDenied('Seu perfil não pode executar esta etapa.')
    anterior = pedido.status
    pedido.status = novo
    pedido.save(update_fields=['status', 'updated_at'])
    HistoricoStatusPedido.objects.create(pedido=pedido, status_anterior=anterior,
        status_novo=novo, alterado_por=user)
    return pedido


@transaction.atomic
def pedir_conta(mesa_uuid, sessao_id):
    mesa = get_object_or_404(Mesa.objects.select_for_update(), token_uuid=mesa_uuid, ativa=True)
    sessao = get_object_or_404(SessaoMesa.objects.select_for_update(), mesa=mesa, pk=sessao_id, ativa=True)
    sessao.conta_solicitada = True
    sessao.save(update_fields=['conta_solicitada'])
    return sessao


def validar_finalizacao(sessao):
    if sessao.pedidos.exclude(status__in=['ENTREGUE', 'CANCELADO']).exists():
        erro('Todos os pedidos devem estar entregues ou cancelados para fechar a conta.')


def encerrar(sessao):
    sessao.ativa = False
    sessao.conta_solicitada = False
    sessao.fechada_em = timezone.now()
    sessao.save(update_fields=['ativa', 'conta_solicitada', 'fechada_em'])


@transaction.atomic
def pagar(sessao_id, meio, user):
    papel(user, ('ADMIN', 'GARCOM'))
    if meio not in dict(Conta.MEIO_PAGAMENTO_CHOICES):
        erro('Meio de pagamento inválido.')
    sessao = sessao_bloqueada(sessao_id)
    if not sessao.ativa:
        erro('Esta sessão já foi encerrada; nenhum pagamento adicional foi registrado.')
    validar_finalizacao(sessao)
    conta, _ = Conta.objects.get_or_create(sessao=sessao)
    conta.calcular_total()
    conta.meio_pagamento, conta.pago, conta.pago_em = meio, True, timezone.now()
    conta.save()
    encerrar(sessao)
    return conta


@transaction.atomic
def fechar(sessao_id, user):
    papel(user, ('ADMIN', 'GARCOM'))
    sessao = sessao_bloqueada(sessao_id)
    if not sessao.ativa:
        erro('A sessão já foi encerrada.')
    validar_finalizacao(sessao)
    total = sum((p.valor_total for p in sessao.pedidos.exclude(status='CANCELADO')), Decimal('0.00'))
    if total > 0:
        erro('A conta ainda não foi paga. Confirme o pagamento para encerrar a sessão.')
    encerrar(sessao)
    return sessao
