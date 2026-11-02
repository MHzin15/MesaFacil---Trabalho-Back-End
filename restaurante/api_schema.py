"""Contratos dos endpoints compostos; os CRUD usam ModelSerializer."""
from rest_framework import serializers
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes
from .serializers import MesaClienteSerializer, MesaSerializer, PedidoSerializer, PedidoCozinhaSerializer, ContaSerializer, PerfilSerializer, SessaoMesaSerializer


class ComandaAcessivelSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    conta_solicitada = serializers.BooleanField()


class CompartilharSerializer(serializers.Serializer):
    url = serializers.CharField()
    qr_url = serializers.CharField()
    expira_em = serializers.DateTimeField()


class SelecionarComandaSerializer(serializers.Serializer):
    comanda_id = serializers.IntegerField(min_value=1)


class MensagemSerializer(serializers.Serializer):
    mensagem = serializers.CharField()


class MesaContextoSerializer(MesaClienteSerializer):
    sessao_ativa = serializers.BooleanField()
    sessao_id = serializers.IntegerField(allow_null=True)
    acesso_liberado = serializers.BooleanField()
    atendimento_encerrado = serializers.BooleanField()
    atendimento_id = serializers.UUIDField(allow_null=True)
    comandas = ComandaAcessivelSerializer(many=True)

    class Meta(MesaClienteSerializer.Meta):
        fields = MesaClienteSerializer.Meta.fields + ['sessao_ativa', 'sessao_id', 'acesso_liberado', 'atendimento_encerrado', 'atendimento_id', 'comandas']


class ContaMesaSerializer(serializers.Serializer):
    mesa = MesaClienteSerializer()
    sessao_id = serializers.IntegerField(allow_null=True)
    pedidos = PedidoSerializer(many=True)
    valor_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    conta_solicitada = serializers.BooleanField()
    versao_conta = serializers.IntegerField()


class CozinhaSerializer(serializers.Serializer):
    RECEBIDO = PedidoCozinhaSerializer(many=True)
    EM_PREPARACAO = PedidoCozinhaSerializer(many=True)
    PRONTO = PedidoCozinhaSerializer(many=True)


class GarcomSerializer(serializers.Serializer):
    pedidos_prontos = PedidoSerializer(many=True)
    mesas_aguardando_conta = MesaSerializer(many=True)
    comandas_aguardando_conta = SessaoMesaSerializer(many=True)


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
