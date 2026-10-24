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
    nome_completo = serializers.CharField(source='user.get_full_name', read_only=True)

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
    def validate(self, attrs):
        if self.instance and attrs.get('ativa') is False and self.instance.sessoes.filter(ativa=True).exists():
            raise serializers.ValidationError('Encerre a sessão antes de desativar a mesa.')
        return attrs

    status = serializers.ReadOnlyField(source='status_display')
    sessao_ativa_id = serializers.SerializerMethodField()
    qr_code = serializers.SerializerMethodField()

    def get_qr_code(self, obj) -> str:
        from django.urls import reverse
        return reverse('qr-download', args=[obj.pk])

    class Meta:
        model = Mesa
        fields = ['id', 'numero', 'token_uuid', 'ativa', 'qr_code', 'status', 'sessao_ativa_id']
        read_only_fields = ['token_uuid', 'qr_code']

    def get_sessao_ativa_id(self, obj) -> int | None:
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
    subtotal = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

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
    quantidade = serializers.IntegerField(min_value=1, max_value=99, default=1)
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
    sessao_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    observacao = serializers.CharField(required=False, default='', allow_blank=True)
    itens = ItemPedidoCriarSerializer(many=True, min_length=1, max_length=100)
    chave_envio = serializers.UUIDField(required=False)
    total_esperado = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False)


class PedidoSerializer(serializers.ModelSerializer):
    itens = ItemPedidoSerializer(many=True, read_only=True)
    mesa_numero = serializers.ReadOnlyField(source='sessao.mesa.numero')
    valor_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Pedido
        fields = [
            'id', 'sessao', 'mesa_numero', 'status',
            'observacao', 'created_at', 'updated_at',
            'itens', 'valor_total', 'chave_envio',
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

    def get_proximo_status(self, obj) -> str | None:
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

    def get_alterado_por_nome(self, obj) -> str:
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


class FiltroDatasSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Pedido.STATUS_CHOICES, required=False)
    data_inicio = serializers.DateField(required=False)
    data_fim = serializers.DateField(required=False)

    def validate(self, attrs):
        if attrs.get('data_inicio') and attrs.get('data_fim') and attrs['data_inicio'] > attrs['data_fim']:
            raise serializers.ValidationError('A data inicial deve ser anterior ou igual à final.')
        return attrs
