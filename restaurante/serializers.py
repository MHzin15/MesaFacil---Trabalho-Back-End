from rest_framework import serializers
from .models import (
    Perfil, Mesa, SessaoMesa, Categoria, Produto, Adicional,
    Pedido, ItemPedido, ItemPedidoAdicional, HistoricoStatusPedido, Conta,
)


# ============================================================
# Perfil
# ============================================================
class PerfilSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    nome_completo = serializers.ReadOnlyField(source='user.get_full_name')

    class Meta:
        model = Perfil
        fields = ['id', 'username', 'nome_completo', 'role']


# ============================================================
# Cardápio
# ============================================================
class AdicionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Adicional
        fields = ['id', 'nome', 'preco', 'produto']


class ProdutoSerializer(serializers.ModelSerializer):
    adicionais = AdicionalSerializer(many=True, read_only=True)
    categoria_nome = serializers.ReadOnlyField(source='categoria.nome')

    class Meta:
        model = Produto
        fields = [
            'id', 'nome', 'descricao', 'preco', 'foto',
            'disponivel', 'categoria', 'categoria_nome', 'adicionais',
        ]


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nome', 'ordem']


class CategoriaComProdutosSerializer(serializers.ModelSerializer):
    """Serializer para exibir o cardápio completo agrupado por categoria."""
    produtos = ProdutoSerializer(many=True, read_only=True)

    class Meta:
        model = Categoria
        fields = ['id', 'nome', 'ordem', 'produtos']


# ============================================================
# Mesa
# ============================================================
class MesaSerializer(serializers.ModelSerializer):
    status = serializers.ReadOnlyField(source='status_display')
    sessao_ativa_id = serializers.SerializerMethodField()

    class Meta:
        model = Mesa
        fields = ['id', 'numero', 'token_uuid', 'ativa', 'qr_code', 'status', 'sessao_ativa_id']
        read_only_fields = ['token_uuid', 'qr_code']

    def get_sessao_ativa_id(self, obj):
        sessao = obj.sessao_ativa
        return sessao.id if sessao else None


class MesaClienteSerializer(serializers.ModelSerializer):
    """Serializer para o cliente — não expõe dados sensíveis."""
    status = serializers.ReadOnlyField(source='status_display')

    class Meta:
        model = Mesa
        fields = ['id', 'numero', 'status']


# ============================================================
# Sessão da Mesa
# ============================================================
class SessaoMesaSerializer(serializers.ModelSerializer):
    mesa_numero = serializers.ReadOnlyField(source='mesa.numero')

    class Meta:
        model = SessaoMesa
        fields = [
            'id', 'mesa', 'mesa_numero', 'ativa',
            'conta_solicitada', 'aberta_em', 'fechada_em', 'aberta_por',
        ]
        read_only_fields = ['aberta_em', 'fechada_em', 'aberta_por']


# ============================================================
# Pedido — Itens e Adicionais
# ============================================================
class ItemPedidoAdicionalSerializer(serializers.ModelSerializer):
    nome = serializers.ReadOnlyField(source='adicional.nome')

    class Meta:
        model = ItemPedidoAdicional
        fields = ['id', 'adicional', 'nome', 'preco']
        read_only_fields = ['preco']


class ItemPedidoSerializer(serializers.ModelSerializer):
    produto_nome = serializers.ReadOnlyField(source='produto.nome')
    itens_adicionais = ItemPedidoAdicionalSerializer(many=True, read_only=True)
    subtotal = serializers.ReadOnlyField()

    class Meta:
        model = ItemPedido
        fields = [
            'id', 'produto', 'produto_nome', 'quantidade',
            'preco_unitario', 'observacao', 'itens_adicionais', 'subtotal',
        ]
        read_only_fields = ['preco_unitario']


class ItemPedidoCriarSerializer(serializers.Serializer):
    """Serializer para criar item dentro de um pedido (nested)."""
    produto_id = serializers.IntegerField()
    quantidade = serializers.IntegerField(min_value=1, default=1)
    observacao = serializers.CharField(
        required=False, default='', allow_blank=True, max_length=255,
    )
    adicionais_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
    )

    def validate_adicionais_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError('Não repita o mesmo adicional no item.')
        return value


class PedidoCriarSerializer(serializers.Serializer):
    """
    Serializer para criar um pedido completo com itens e adicionais.
    Recebe o token_uuid da mesa e uma lista de itens.
    """
    mesa_uuid = serializers.UUIDField()
    observacao = serializers.CharField(required=False, default='', allow_blank=True)
    itens = ItemPedidoCriarSerializer(many=True, min_length=1)


class PedidoSerializer(serializers.ModelSerializer):
    itens = ItemPedidoSerializer(many=True, read_only=True)
    mesa_numero = serializers.ReadOnlyField(source='sessao.mesa.numero')
    valor_total = serializers.ReadOnlyField()

    class Meta:
        model = Pedido
        fields = [
            'id', 'sessao', 'mesa_numero', 'status',
            'observacao', 'created_at', 'updated_at',
            'itens', 'valor_total',
        ]
        read_only_fields = ['sessao', 'created_at', 'updated_at']


class PedidoStatusSerializer(serializers.Serializer):
    """Serializer para alterar o status de um pedido."""
    status = serializers.ChoiceField(choices=Pedido.STATUS_CHOICES)


class ProdutoDisponibilidadeSerializer(serializers.Serializer):
    disponivel = serializers.BooleanField()

    def validate_disponivel(self, value):
        if not isinstance(self.initial_data['disponivel'], bool):
            raise serializers.ValidationError('Informe um booleano JSON (true/false).')
        return value


class PedidoCozinhaSerializer(PedidoSerializer):
    """Dados do cartão e ações de preparo para atualização por polling."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    proximo_status = serializers.SerializerMethodField()

    class Meta(PedidoSerializer.Meta):
        fields = PedidoSerializer.Meta.fields + ['status_display', 'proximo_status']

    def get_proximo_status(self, obj):
        return {'RECEBIDO': 'EM_PREPARACAO', 'EM_PREPARACAO': 'PRONTO'}.get(obj.status)


# ============================================================
# Histórico de Status
# ============================================================
class HistoricoStatusPedidoSerializer(serializers.ModelSerializer):
    alterado_por_nome = serializers.SerializerMethodField()

    class Meta:
        model = HistoricoStatusPedido
        fields = [
            'id', 'pedido', 'status_anterior', 'status_novo',
            'alterado_em', 'alterado_por', 'alterado_por_nome',
        ]

    def get_alterado_por_nome(self, obj):
        if obj.alterado_por:
            return obj.alterado_por.get_full_name() or obj.alterado_por.username
        return 'Cliente'


# ============================================================
# Conta / Pagamento
# ============================================================
class ContaSerializer(serializers.ModelSerializer):
    mesa_numero = serializers.ReadOnlyField(source='sessao.mesa.numero')

    class Meta:
        model = Conta
        fields = [
            'id', 'sessao', 'mesa_numero', 'valor_total',
            'meio_pagamento', 'pago', 'pago_em', 'criado_em',
        ]
        read_only_fields = ['sessao', 'valor_total', 'pago', 'pago_em', 'criado_em']


class PagamentoSerializer(serializers.Serializer):
    """Serializer para processar pagamento simulado."""
    meio_pagamento = serializers.ChoiceField(choices=Conta.MEIO_PAGAMENTO_CHOICES)
