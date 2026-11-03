"""Compatibilidade de rotas antigas e transferência exclusiva autorizada pela equipe."""
from django.shortcuts import get_object_or_404, render
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import Mesa
from .permissions import IsGarcomOuAdmin
from .api_schema import MensagemSerializer, TrocaResponsavelSerializer, ERROS
from .security import destino_comanda
from . import atendimento


@extend_schema(request=None, responses={410: MensagemSerializer})
@api_view(['POST'])
@permission_classes([AllowAny])
def compartilhar(request, uuid):
    return Response({'mensagem': 'Convites foram desativados. A mesa tem um único responsável.'}, status=410)


@extend_schema(request=None, responses={410: MensagemSerializer})
@api_view(['GET'])
@permission_classes([AllowAny])
def convite_qr(request, uuid, token):
    return Response({'mensagem': 'Este convite não é mais válido.'}, status=410)


@extend_schema(request=None, responses={410: MensagemSerializer})
@api_view(['POST'])
@permission_classes([AllowAny])
def selecionar(request, uuid):
    return Response({'mensagem': 'A troca de responsável é feita somente pela equipe.'}, status=410)


def convite(request, token):
    response = render(request, 'restaurante/convite_desativado.html', status=410)
    response['Cache-Control'] = 'no-store'
    return response


@extend_schema(request=None, responses={200: MensagemSerializer, **ERROS})
@api_view(['POST'])
@permission_classes([AllowAny])
def atividade(request, uuid):
    mesa = get_object_or_404(Mesa, token_uuid=uuid, ativa=True)
    atendimento.registrar_atividade(mesa, destino_comanda(request, mesa))
    return Response({'mensagem': 'Atividade registrada.'})


@extend_schema(request=None, responses={200: TrocaResponsavelSerializer, **ERROS})
@api_view(['POST'])
@permission_classes([AllowAny])
def solicitar_transferencia(request, uuid):
    mesa = get_object_or_404(Mesa, token_uuid=uuid, ativa=True)
    troca = atendimento.solicitar_troca(request, mesa)
    return Response({'id': troca.pk, 'codigo': troca.codigo, 'expira_em': troca.expira_em})


@extend_schema(request=None, responses={200: MensagemSerializer, **ERROS})
@api_view(['POST'])
@permission_classes([IsGarcomOuAdmin])
def autorizar_transferencia(request, pk):
    atendimento.autorizar_troca(pk, request.user)
    return Response({'mensagem': 'Novo responsável autorizado. O aparelho anterior perdeu o acesso; os pedidos foram mantidos.'})
