"""Regras transacionais compartilhadas pela API e pelo admin."""
import hashlib
import json
from decimal import Decimal
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from restaurante.security import usuario_garcom
from restaurante.opcoes import selecionar_opcoes
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
            if mesa.sessoes.filter(ativa=True).exists():
                erro(f'Mesa {mesa.numero} já possui uma sessão aberta.')
            return SessaoMesa.objects.create(mesa=mesa, aberta_por=user)
    except IntegrityError:
        if SessaoMesa.objects.filter(mesa_id=mesa_id, ativa=True).exists():
            erro('Esta mesa já possui uma sessão aberta.')
        raise


@transaction.atomic
def criar(dados, user, *, geracao=None):
    if usuario_garcom(user):
        raise PermissionDenied('O perfil de garçom não pode criar pedidos.')
    if dados.get('atendimento_id') and str(dados['atendimento_id']) != str(geracao):
        erro('O destino da tentativa não corresponde à comanda autorizada.')
    mesa = get_object_or_404(Mesa.objects.select_for_update(), token_uuid=dados['mesa_uuid'], ativa=True)
    if geracao is not None:
        from restaurante.atendimento import validar_responsavel
        validar_responsavel(mesa, geracao)
        sessao = SessaoMesa.objects.select_for_update().filter(mesa=mesa, acesso_uuid=geracao).first()
        if sessao and not sessao.ativa:
            erro('Esta comanda foi encerrada. Comece uma nova comanda para pedir novamente.')
        if not sessao:
            if mesa.sessoes.filter(ativa=True).exists():
                erro('Esta mesa já está em atendimento.')
            if dados.get('sessao_id') is not None:
                erro('A comanda mudou. Revise seu pedido antes de enviar.')
            sessao = SessaoMesa.objects.create(mesa=mesa, acesso_uuid=geracao,
                aberta_por=user if user.is_authenticated else None)
        if mesa.reserva_ate is not None:
            mesa.reserva_ate = None
            mesa.save(update_fields=['reserva_ate'])
    else:
        sessao = SessaoMesa.objects.select_for_update().filter(mesa=mesa, ativa=True, pk=dados.get('sessao_id')).first()
    if not sessao:
        erro('Esta comanda não está aberta.')
    if dados.get('sessao_id') != sessao.pk and not (geracao is not None and dados.get('sessao_id') is None):
        erro('A comanda mudou ou foi encerrada. Revise o pedido.')
    key = dados.get('chave_envio')
    # O destino já pertence ao escopo da chave; manter o hash de clientes anteriores.
    conteudo = {k: v for k, v in dados.items() if k != 'atendimento_id'}
    digest = hashlib.sha256(json.dumps(conteudo, sort_keys=True, default=str).encode()).hexdigest()
    if key:
        anterior = sessao.pedidos.filter(chave_envio=key).first()
        if anterior:
            if anterior.envio_hash != digest:
                erro('Esta chave de envio já foi usada com outro pedido. Revise e envie novamente.')
            return Pedido.objects.para_exibicao().get(pk=anterior.pk)
    if sessao.conta_solicitada:
        erro('A conta está em fechamento. Peça à equipe para retomar o atendimento antes de pedir.')
    # FOR NO KEY UPDATE preserva preço/disponibilidade, mas permite KEY SHARE
    # da FK ao editar o produto de um adicional (evita ciclo Produto ↔ Adicional).
    products = {p.pk: p for p in Produto.objects.select_for_update(no_key=True).filter(
        pk__in=[i['produto_id'] for i in dados['itens']]).order_by('pk')}
    addons = {a.pk: a for a in Adicional.objects.select_for_update().filter(
        pk__in=[a for i in dados['itens'] for a in i.get('adicionais_ids', [])]).order_by('pk')}
    pedido = Pedido.objects.create(sessao=sessao, observacao=dados.get('observacao', ''), chave_envio=key, envio_hash=digest)
    HistoricoStatusPedido.objects.create(pedido=pedido, status_novo='RECEBIDO',
        alterado_por=user if user.is_authenticated else None)
    for item in dados['itens']:
        produto = products.get(item['produto_id'])
        if not produto:
            get_object_or_404(Produto, pk=item['produto_id'])
        if not produto.disponivel:
            erro(f'O produto "{produto.nome}" está indisponível.')
        saved = ItemPedido.objects.create(pedido=pedido, produto=produto,
            quantidade=item['quantidade'], preco_unitario=produto.preco, observacao=item.get('observacao', ''),
            opcoes=selecionar_opcoes(produto, item.get('opcoes', []), item.get('opcoes_versao')))
        for aid in item.get('adicionais_ids', []):
            adicional = addons.get(aid)
            if not adicional or adicional.produto_id != produto.pk:
                from django.http import Http404
                raise Http404('Adicional não pertence ao produto.')
            ItemPedidoAdicional.objects.create(item_pedido=saved, adicional=adicional, preco=adicional.preco)
    pedido = Pedido.objects.para_exibicao().get(pk=pedido.pk)
    if dados.get('total_esperado') is not None and pedido.valor_total != dados['total_esperado']:
        erro('Os preços mudaram. Atualize o cardápio e confirme novamente o total.')
    total = sessao.total_consumo()
    if total > Decimal('99999999.99'):
        erro('O total ultrapassa o limite da conta. Peça ajuda ao atendimento.')
    atualizar_versao(sessao)
    return pedido


def atualizar_versao(sessao):
    # Chamado somente após bloquear a mesa e a sessão na transação.
    sessao.versao_conta += 1
    sessao.save(update_fields=['versao_conta'])


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
    atualizar_versao(sessao)
    return Pedido.objects.para_exibicao().get(pk=pedido.pk)


@transaction.atomic
def pedir_conta(mesa_uuid, sessao_id, *, geracao=None):
    mesa = get_object_or_404(Mesa.objects.select_for_update(), token_uuid=mesa_uuid, ativa=True)
    sessao = get_object_or_404(SessaoMesa.objects.select_for_update(), mesa=mesa, pk=sessao_id, ativa=True)
    if geracao is not None:
        from restaurante.atendimento import validar_responsavel
        validar_responsavel(mesa, geracao)
    if not sessao.conta_solicitada:
        sessao.conta_solicitada = True
        sessao.conta_solicitada_em = timezone.now()
        sessao.save(update_fields=['conta_solicitada', 'conta_solicitada_em'])
        atualizar_versao(sessao)
    return sessao


@transaction.atomic
def retomar(sessao_id, user):
    papel(user, ('ADMIN', 'GARCOM'))
    sessao = sessao_bloqueada(sessao_id)
    if not sessao.ativa:
        erro('A sessão foi encerrada.')
    if sessao.conta_solicitada:
        sessao.conta_solicitada = False
        sessao.conta_solicitada_em = None
        sessao.save(update_fields=['conta_solicitada', 'conta_solicitada_em'])
        atualizar_versao(sessao)
        auditar(user, sessao, 'Atendimento retomado; conferência anterior invalidada.')
    return sessao


def auditar(user, obj, mensagem):
    from django.contrib.admin.models import LogEntry, CHANGE
    from django.contrib.contenttypes.models import ContentType
    LogEntry.objects.create(user=user, content_type=ContentType.objects.get_for_model(obj),
        object_id=str(obj.pk), object_repr=str(obj)[:200], action_flag=CHANGE, change_message=mensagem)


@transaction.atomic
def cancelar_excepcional(pedido_id, motivo, user):
    papel(user, ('ADMIN',))
    motivo = motivo.strip()
    if len(motivo) < 10 or len(motivo) > 500:
        erro('Explique o motivo do cancelamento em 10 a 500 caracteres.')
    ref = get_object_or_404(Pedido, pk=pedido_id)
    sessao = sessao_bloqueada(ref.sessao_id)
    pedido = get_object_or_404(Pedido.objects.select_for_update(), pk=pedido_id)
    if not sessao.ativa or Conta.objects.filter(sessao=sessao, pago=True).exists():
        erro('Conta encerrada ou paga. Cancelamento não substitui devolução de pagamento.')
    if pedido.status == 'CANCELADO':
        erro('O pedido já está cancelado.')
    anterior = pedido.status
    pedido.status = 'CANCELADO'
    pedido.save(update_fields=['status', 'updated_at'])
    HistoricoStatusPedido.objects.create(pedido=pedido, status_anterior=anterior,
        status_novo='CANCELADO', alterado_por=user, motivo=motivo)
    atualizar_versao(sessao)
    auditar(user, pedido, f'Cancelamento excepcional ({anterior}): {motivo}')
    return pedido


def validar_finalizacao(sessao):
    if sessao.pedidos.exclude(status__in=['ENTREGUE', 'CANCELADO']).exists():
        erro('Todos os pedidos devem estar entregues ou cancelados para fechar a conta.')


def encerrar(sessao):
    sessao.ativa = False
    sessao.conta_solicitada = False
    sessao.fechada_em = timezone.now()
    sessao.save(update_fields=['ativa', 'conta_solicitada', 'fechada_em'])
    if not SessaoMesa.objects.filter(mesa_id=sessao.mesa_id, ativa=True).exists():
        Mesa.objects.filter(pk=sessao.mesa_id).update(responsavel_uuid=None, reserva_ate=None)


@transaction.atomic
def pagar(sessao_id, meio, user, *, total_esperado, versao_conta):
    papel(user, ('ADMIN', 'GARCOM'))
    if meio not in dict(Conta.MEIO_PAGAMENTO_CHOICES):
        erro('Meio de pagamento inválido.')
    sessao = sessao_bloqueada(sessao_id)
    if not sessao.ativa:
        erro('Esta sessão já foi encerrada; nenhum pagamento adicional foi registrado.')
    validar_finalizacao(sessao)
    total = sessao.total_consumo()
    if sessao.versao_conta != versao_conta or total != total_esperado:
        erro('A conta mudou. Confira novamente o total e confirme o pagamento.')
    conta, _ = Conta.objects.get_or_create(sessao=sessao)
    conta.valor_total = total
    conta.meio_pagamento, conta.pago, conta.pago_em = meio, True, timezone.now()
    conta.save()
    auditar(user, conta, f'Pagamento simulado confirmado: {meio}, R$ {total}.')
    encerrar(sessao)
    return conta


@transaction.atomic
def fechar(sessao_id, user):
    papel(user, ('ADMIN', 'GARCOM'))
    sessao = sessao_bloqueada(sessao_id)
    if not sessao.ativa:
        erro('A sessão já foi encerrada.')
    validar_finalizacao(sessao)
    total = sessao.total_consumo()
    if total > 0:
        erro('A conta ainda não foi paga. Confirme o pagamento para encerrar a sessão.')
    encerrar(sessao)
    return sessao
