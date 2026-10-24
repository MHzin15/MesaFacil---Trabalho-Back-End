"""Contratos dos endpoints compostos; os CRUD usam ModelSerializer."""
from rest_framework import serializers
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes
from .serializers import MesaClienteSerializer, MesaSerializer, PedidoSerializer, PedidoCozinhaSerializer, ContaSerializer, PerfilSerializer


class MensagemSerializer(serializers.Serializer):
    mensagem = serializers.CharField()


class MesaContextoSerializer(MesaClienteSerializer):
    sessao_ativa = serializers.BooleanField()
    sessao_id = serializers.IntegerField(allow_null=True)

    class Meta(MesaClienteSerializer.Meta):
        fields = MesaClienteSerializer.Meta.fields + ['sessao_ativa', 'sessao_id']


class ContaMesaSerializer(serializers.Serializer):
    mesa = MesaClienteSerializer()
    sessao_id = serializers.IntegerField()
    pedidos = PedidoSerializer(many=True)
    valor_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    conta_solicitada = serializers.BooleanField()


class CozinhaSerializer(serializers.Serializer):
    RECEBIDO = PedidoCozinhaSerializer(many=True)
    EM_PREPARACAO = PedidoCozinhaSerializer(many=True)
    PRONTO = PedidoCozinhaSerializer(many=True)


class GarcomSerializer(serializers.Serializer):
    pedidos_prontos = PedidoSerializer(many=True)
    mesas_aguardando_conta = MesaSerializer(many=True)


class PagamentoResultadoSerializer(MensagemSerializer):
    conta = ContaSerializer()


class UsuarioSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    nome = serializers.CharField()
    is_staff = serializers.BooleanField()
    perfil = PerfilSerializer(required=False)


class QrLinksSerializer(serializers.Serializer):
    qr_code_url = serializers.URLField()
    mesa_url = serializers.URLField()


FILTROS = [OpenApiParameter('data_inicio', OpenApiTypes.DATE), OpenApiParameter('data_fim', OpenApiTypes.DATE)]
ERROS = {400: OpenApiTypes.OBJECT, 403: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
