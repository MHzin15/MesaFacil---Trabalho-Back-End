"""Compartilhamento explícito; o QR público da mesa não é uma credencial de conta."""
from datetime import timedelta
from io import BytesIO

import qrcode
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema, OpenApiTypes
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from . import services
from .api_schema import ERROS, CompartilharSerializer, MensagemSerializer, SelecionarComandaSerializer
from .models import ConviteComanda, Mesa
from .security import validar_mesa, guardar_comanda, comandas_acessiveis


@extend_schema(request=None, responses={200: CompartilharSerializer, **ERROS})
@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def compartilhar(request, uuid):
    mesa = get_object_or_404(Mesa, token_uuid=uuid, ativa=True)
    sessao = validar_mesa(request, mesa)
    if not sessao:
        raise ValidationError({'erro': 'Envie o primeiro pedido antes de compartilhar a comanda.'})
    sessao = services.sessao_bloqueada(sessao.pk)
    if not sessao.ativa:
        raise ValidationError({'erro': 'Esta comanda foi encerrada.'})
    convite = sessao.convites.filter(expira_em__gt=timezone.now()).first()
    if not convite:
        convite = ConviteComanda.objects.create(sessao=sessao, expira_em=timezone.now() + timedelta(minutes=15))
    return Response({
        'url': request.build_absolute_uri(reverse('convite-comanda', args=[convite.token])),
        'qr_url': reverse('convite-qr', args=[uuid, convite.token]),
        'expira_em': convite.expira_em,
    })


@extend_schema(request=None, responses={200: OpenApiTypes.BINARY, **ERROS})
@api_view(['GET'])
@permission_classes([AllowAny])
def convite_qr(request, uuid, token):
    mesa = get_object_or_404(Mesa, token_uuid=uuid, ativa=True)
    sessao = validar_mesa(request, mesa)
    convite = get_object_or_404(ConviteComanda, token=token, sessao=sessao,
                               sessao__ativa=True, expira_em__gt=timezone.now())
    stream = BytesIO()
    qrcode.make(request.build_absolute_uri(reverse('convite-comanda', args=[convite.token]))).save(stream, format='PNG')
    response = HttpResponse(stream.getvalue(), content_type='image/png')
    response['Cache-Control'] = 'no-store'
    return response


@extend_schema(request=SelecionarComandaSerializer, responses={200: MensagemSerializer, **ERROS})
@api_view(['POST'])
@permission_classes([AllowAny])
def selecionar(request, uuid):
    mesa = get_object_or_404(Mesa, token_uuid=uuid, ativa=True)
    serializer = SelecionarComandaSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    sessao = get_object_or_404(comandas_acessiveis(request, mesa), pk=serializer.validated_data['comanda_id'])
    guardar_comanda(request, mesa, sessao.acesso_uuid)
    return Response({'mensagem': 'Comanda selecionada.'})


@ensure_csrf_cookie
def convite(request, token):
    # Uma prévia de link ou GET não inscreve a pessoa nem troca sua comanda atual.
    obj = ConviteComanda.objects.select_related('sessao__mesa').filter(token=token,
        sessao__ativa=True, sessao__mesa__ativa=True, expira_em__gt=timezone.now()).first()
    if request.method == 'POST' and obj:
        with transaction.atomic():
            sessao = services.sessao_bloqueada(obj.sessao_id)
            if not sessao.ativa or not sessao.mesa.ativa or obj.expira_em <= timezone.now():
                obj = None
            else:
                guardar_comanda(request, sessao.mesa, sessao.acesso_uuid)
                response = redirect('cliente', uuid=sessao.mesa.token_uuid)
                response['Referrer-Policy'] = 'same-origin'
                return response
    response = render(request, 'restaurante/convite.html', {'convite': obj}, status=200 if obj else 410)
    response['Cache-Control'] = 'no-store'
    response['Referrer-Policy'] = 'same-origin'
    response['X-Robots-Tag'] = 'noindex, nofollow'
    return response
