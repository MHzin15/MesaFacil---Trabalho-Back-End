"""Um responsável por mesa; reserva sem pedido expira sem serviço agendado."""
from datetime import timedelta
from uuid import uuid4
import secrets

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import Mesa, SessaoMesa, TrocaResponsavel

TEMPO_RESERVA = timedelta(minutes=5)


def ocupada(mesa):
    return mesa.sessoes.filter(ativa=True).exists() or bool(
        mesa.responsavel_uuid and mesa.reserva_ate and mesa.reserva_ate > timezone.now())


def dono(mesa, chave):
    return bool(chave and str(mesa.responsavel_uuid) == str(chave) and (
        mesa.reserva_ate is None or mesa.reserva_ate > timezone.now()))


def revogado(mesa, chave):
    return bool(chave and TrocaResponsavel.objects.filter(mesa=mesa, anterior_uuid=chave,
                                                         autorizada_em__isnull=False).exists())


@transaction.atomic
def assumir(request, mesa, novo=False):
    from .security import chave_comanda, comanda_cliente, guardar_comanda, equipe_mesa
    if equipe_mesa(request.user):
        return
    mesa = get_object_or_404(Mesa.objects.select_for_update(), pk=mesa.pk, ativa=True)
    chave = chave_comanda(request, mesa)
    anterior = comanda_cliente(request, mesa)
    # O aparelho do atendimento encerrado nunca entra no próximo por polling/reload.
    if not novo and ((anterior and not anterior.ativa) or revogado(mesa, chave)):
        return
    if dono(mesa, chave) and not (novo and anterior and not anterior.ativa):
        if mesa.reserva_ate:
            mesa.reserva_ate = timezone.now() + TEMPO_RESERVA
            mesa.save(update_fields=['reserva_ate'])
        return
    if ocupada(mesa):
        return
    chave = uuid4()
    mesa.responsavel_uuid = chave
    mesa.reserva_ate = timezone.now() + TEMPO_RESERVA
    mesa.save(update_fields=['responsavel_uuid', 'reserva_ate'])
    guardar_comanda(request, mesa, chave)


def validar_responsavel(mesa, chave):
    if not dono(mesa, chave):
        raise PermissionDenied('Esta mesa já está em atendimento ou seu acesso expirou. Somente o responsável pode fazer pedidos.')


@transaction.atomic
def registrar_atividade(mesa, chave):
    mesa = get_object_or_404(Mesa.objects.select_for_update(), pk=mesa.pk, ativa=True)
    validar_responsavel(mesa, chave)
    if mesa.reserva_ate:
        mesa.reserva_ate = timezone.now() + TEMPO_RESERVA
        mesa.save(update_fields=['reserva_ate'])


@transaction.atomic
def solicitar_troca(request, mesa):
    from .security import chave_comanda
    mesa = get_object_or_404(Mesa.objects.select_for_update(), pk=mesa.pk, ativa=True)
    if dono(mesa, chave_comanda(request, mesa)) or not ocupada(mesa):
        raise ValidationError('A mesa não precisa de transferência neste momento. Atualize a página.')
    pendentes = request.session.get('trocas_responsavel', {})
    atual = mesa.responsavel_uuid or mesa.sessao_ativa.acesso_uuid
    key = pendentes.get(str(mesa.token_uuid))
    troca = TrocaResponsavel.objects.filter(mesa=mesa, acesso_uuid=key, anterior_uuid=atual,
        expira_em__gt=timezone.now(), autorizada_em__isnull=True).first() if key else None
    if not troca:
        if mesa.trocas_responsavel.filter(autorizada_em__isnull=True, expira_em__gt=timezone.now()).count() >= 10:
            raise ValidationError('Já existem solicitações pendentes para esta mesa. Peça ajuda à equipe ou aguarde 5 minutos.')
        troca = TrocaResponsavel.objects.create(mesa=mesa, anterior_uuid=atual, codigo=secrets.token_hex(4).upper(),
                                               expira_em=timezone.now() + TEMPO_RESERVA)
        pendentes[str(mesa.token_uuid)] = str(troca.acesso_uuid)
        request.session['trocas_responsavel'] = pendentes
    return troca


def reconhecer_transferencia(request, mesa):
    from .security import guardar_comanda
    key = request.session.get('trocas_responsavel', {}).get(str(mesa.token_uuid))
    if key and str(mesa.responsavel_uuid) == key:
        troca = TrocaResponsavel.objects.filter(mesa=mesa, acesso_uuid=key, autorizada_em__isnull=False).exists()
        if troca:
            guardar_comanda(request, mesa, key)


@transaction.atomic
def autorizar_troca(pk, user):
    from .services import papel, auditar
    papel(user, ('ADMIN', 'GARCOM'))
    ref = get_object_or_404(TrocaResponsavel, pk=pk)
    mesa = get_object_or_404(Mesa.objects.select_for_update(), pk=ref.mesa_id, ativa=True)
    troca = get_object_or_404(TrocaResponsavel.objects.select_for_update(), pk=pk,
                             autorizada_em__isnull=True, expira_em__gt=timezone.now())
    sessoes = list(SessaoMesa.objects.select_for_update().filter(mesa=mesa, ativa=True))
    if len(sessoes) > 1:
        raise ValidationError('Esta mesa tem contas anteriores à atualização. Finalize as contas antigas até restar um único atendimento antes de transferir.')
    if not ocupada(mesa):
        raise ValidationError('O atendimento terminou ou a reserva expirou. Leia o QR da mesa novamente.')
    atual = mesa.responsavel_uuid or (sessoes[0].acesso_uuid if sessoes else None)
    if str(troca.anterior_uuid) != str(atual):
        raise ValidationError('O atendimento mudou desde a solicitação. Peça uma nova solicitação no aparelho correto.')
    mesa.responsavel_uuid = troca.acesso_uuid
    mesa.reserva_ate = None if sessoes else timezone.now() + TEMPO_RESERVA
    mesa.save(update_fields=['responsavel_uuid', 'reserva_ate'])
    if sessoes:
        sessao = sessoes[0]
        sessao.acesso_uuid = troca.acesso_uuid
        sessao.save(update_fields=['acesso_uuid'])
    troca.autorizada_em = timezone.now()
    troca.save(update_fields=['autorizada_em', 'anterior_uuid'])
    mesa.trocas_responsavel.exclude(pk=troca.pk).filter(autorizada_em__isnull=True).update(expira_em=timezone.now())
    auditar(user, mesa, f'Responsável transferido para o aparelho da solicitação #{troca.pk}. Acesso anterior revogado; pedidos preservados.')
