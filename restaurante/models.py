from decimal import Decimal
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
import uuid


# ============================================================
# Perfil de usuário (Cozinha, Garçom, Administrador)
# ============================================================
class Perfil(models.Model):
    ROLE_CHOICES = [
        ('ADMIN', 'Administrador'),
        ('COZINHA', 'Cozinha'),
        ('GARCOM', 'Garçom'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil',
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        verbose_name='Perfil',
    )

    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfis'

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} — {self.get_role_display()}"


# ============================================================
# Mesa
# ============================================================
class Mesa(models.Model):
    numero = models.IntegerField(unique=True, verbose_name='Número da Mesa', validators=[MinValueValidator(1)])
    # UUID aleatório para garantir a segurança do QR Code (RNF05)
    token_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    ativa = models.BooleanField(default=True, verbose_name='Mesa Ativa')
    # Imagem do QR Code gerado
    qr_code = models.ImageField(
        upload_to='qrcodes/',
        blank=True,
        null=True,
        verbose_name='QR Code',
    )

    class Meta:
        verbose_name = 'Mesa'
        verbose_name_plural = 'Mesas'
        ordering = ['numero']
        constraints = [models.CheckConstraint(condition=models.Q(numero__gte=1), name='mesa_numero_positivo')]

    def clean(self):
        super().clean()
        if self.pk and not self.ativa and self.sessoes.filter(ativa=True).exists():
            raise ValidationError({'ativa': 'Encerre a sessão antes de desativar a mesa.'})

    def __str__(self):
        return f"Mesa {self.numero}"

    @property
    def sessao_ativa(self):
        """Retorna a sessão ativa da mesa, se houver."""
        return self.sessoes.filter(ativa=True).first()

    @property
    def status_display(self) -> str:
        """Retorna o status visual da mesa."""
        sessao = self.sessao_ativa
        if not sessao:
            return 'livre'
        if sessao.conta_solicitada:
            return 'aguardando_conta'
        return 'ocupada'


# ============================================================
# Sessão da Mesa (RF03, RN04, RN05)
# ============================================================
class SessaoMesa(models.Model):
    mesa = models.ForeignKey(
        Mesa,
        on_delete=models.PROTECT,
        related_name='sessoes',
        verbose_name='Mesa',
    )
    aberta_em = models.DateTimeField(auto_now_add=True, verbose_name='Aberta em')
    fechada_em = models.DateTimeField(blank=True, null=True, verbose_name='Fechada em')
    ativa = models.BooleanField(default=True, verbose_name='Sessão Ativa')
    conta_solicitada = models.BooleanField(
        default=False,
        verbose_name='Conta Solicitada',
    )
    aberta_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessoes_abertas',
        verbose_name='Aberta por',
    )

    class Meta:
        verbose_name = 'Sessão da Mesa'
        verbose_name_plural = 'Sessões das Mesas'
        ordering = ['-aberta_em']
        constraints = [
            models.UniqueConstraint(
                fields=['mesa'], condition=models.Q(ativa=True),
                name='uma_sessao_ativa_por_mesa',
            ),
        ]

    def __str__(self):
        status = 'Ativa' if self.ativa else 'Encerrada'
        return f"Sessão Mesa {self.mesa.numero} — {status}"


# ============================================================
# Cardápio: Categoria, Produto, Adicional
# ============================================================
class Categoria(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    ordem = models.IntegerField(default=0, verbose_name='Ordem de Exibição')

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering = ['ordem', 'nome']

    def __str__(self):
        return self.nome


class Produto(models.Model):
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name='produtos',
    )
    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True, verbose_name='Descrição')
    preco = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Preço (R$)', validators=[MinValueValidator(Decimal('0.00'))],
    )
    foto = models.ImageField(
        upload_to='produtos/',
        blank=True,
        null=True,
        verbose_name='Foto',
    )
    disponivel = models.BooleanField(
        default=True,
        verbose_name='Disponível no Cardápio',
    )  # RF07, RF15

    class Meta:
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        ordering = ['categoria__ordem', 'nome']
        constraints = [models.CheckConstraint(condition=models.Q(preco__gte=0), name='produto_preco_valido')]

    def __str__(self):
        return f"{self.nome} — R$ {self.preco}"


class Adicional(models.Model):
    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name='adicionais',
    )
    nome = models.CharField(max_length=100)
    preco = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Preço (R$)', validators=[MinValueValidator(Decimal('0.00'))],
    )

    class Meta:
        verbose_name = 'Adicional'
        verbose_name_plural = 'Adicionais'
        constraints = [models.CheckConstraint(condition=models.Q(preco__gte=0), name='adicional_preco_valido')]

    def __str__(self):
        return f"{self.nome} (+R$ {self.preco})"


# ============================================================
# Pedido e Itens (RN01–RN08)
# ============================================================
class Pedido(models.Model):
    STATUS_CHOICES = [
        ('RECEBIDO', 'Recebido'),
        ('EM_PREPARACAO', 'Em Preparação'),
        ('PRONTO', 'Pronto'),
        ('A_CAMINHO', 'A Caminho'),
        ('ENTREGUE', 'Entregue'),
        ('CANCELADO', 'Cancelado'),
    ]

    # Sequência válida de transições (RN01)
    TRANSICOES_VALIDAS = {
        'RECEBIDO': ['EM_PREPARACAO', 'CANCELADO'],
        'EM_PREPARACAO': ['PRONTO'],
        'PRONTO': ['A_CAMINHO'],
        'A_CAMINHO': ['ENTREGUE'],
        'ENTREGUE': [],
        'CANCELADO': [],
    }

    chave_envio = models.UUIDField(null=True, blank=True, editable=False)
    envio_hash = models.CharField(max_length=64, default='', editable=False)

    sessao = models.ForeignKey(
        SessaoMesa,
        on_delete=models.PROTECT,
        related_name='pedidos',
        verbose_name='Sessão',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='RECEBIDO',
    )
    observacao = models.TextField(
        blank=True,
        default='',
        verbose_name='Observação Geral',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-created_at']
        constraints = [models.UniqueConstraint(fields=['sessao', 'chave_envio'], name='pedido_envio_unico')]

    def __str__(self):
        return (
            f"Pedido #{self.id} — Mesa {self.sessao.mesa.numero} "
            f"({self.get_status_display()})"
        )

    @property
    def valor_total(self):
        """Soma de todos os itens do pedido."""
        return sum((item.subtotal for item in self.itens.all()), Decimal('0.00'))

    def pode_transitar_para(self, novo_status):
        """Verifica se a transição de status é permitida (RN01)."""
        return novo_status in self.TRANSICOES_VALIDAS.get(self.status, [])

    def pode_cancelar(self):
        """Pedido só pode ser cancelado antes de entrar em preparação (RN02)."""
        return self.status == 'RECEBIDO'


class ItemPedido(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='itens',
    )
    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        related_name='itens_pedido',
    )
    quantidade = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    # Preço gravado no momento do pedido (RNF08)
    preco_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Preço Unitário (gravado)', validators=[MinValueValidator(Decimal('0.00'))],
    )
    observacao = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name='Observação do Item',
    )

    class Meta:
        verbose_name = 'Item do Pedido'
        verbose_name_plural = 'Itens do Pedido'
        constraints = [
            models.CheckConstraint(condition=models.Q(quantidade__gte=1), name='item_quantidade_positiva'),
            models.CheckConstraint(condition=models.Q(preco_unitario__gte=0), name='item_preco_valido'),
        ]

    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome} (Pedido #{self.pedido_id})"

    @property
    def total_adicionais(self):
        """Soma dos preços dos adicionais gravados neste item."""
        return sum(
            ia.preco for ia in self.itens_adicionais.all()
        )

    @property
    def subtotal(self):
        """(preço do produto + adicionais) × quantidade (RN06)."""
        return (self.preco_unitario + self.total_adicionais) * self.quantidade


class ItemPedidoAdicional(models.Model):
    """
    Tabela intermediária para gravar o preço do adicional no momento
    do pedido, garantindo integridade de valores (RNF08).
    """
    item_pedido = models.ForeignKey(
        ItemPedido,
        on_delete=models.CASCADE,
        related_name='itens_adicionais',
    )
    adicional = models.ForeignKey(
        Adicional,
        on_delete=models.PROTECT,
        related_name='itens_pedido',
    )
    preco = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Preço do Adicional (gravado)', validators=[MinValueValidator(Decimal('0.00'))],
    )

    class Meta:
        verbose_name = 'Adicional do Item'
        verbose_name_plural = 'Adicionais dos Itens'
        constraints = [models.CheckConstraint(condition=models.Q(preco__gte=0), name='item_adicional_preco_valido')]

    def __str__(self):
        return f"{self.adicional.nome} — R$ {self.preco}"


# ============================================================
# Histórico de Status (RN03)
# ============================================================
class HistoricoStatusPedido(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='historico_status',
    )
    status_anterior = models.CharField(max_length=20, blank=True, default='')
    status_novo = models.CharField(max_length=20)
    alterado_em = models.DateTimeField(auto_now_add=True)
    alterado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Alterado por',
    )

    class Meta:
        verbose_name = 'Histórico de Status'
        verbose_name_plural = 'Históricos de Status'
        ordering = ['alterado_em']

    def __str__(self):
        return (
            f"Pedido #{self.pedido_id}: "
            f"{self.status_anterior or '—'} → {self.status_novo} "
            f"em {self.alterado_em:%d/%m/%Y %H:%M}"
        )


# ============================================================
# Conta / Pagamento Simulado (RF19–RF22, RN09–RN10)
# ============================================================
class Conta(models.Model):
    MEIO_PAGAMENTO_CHOICES = [
        ('PIX', 'Pix'),
        ('CARTAO', 'Cartão'),
        ('DINHEIRO', 'Dinheiro no Caixa'),
    ]

    sessao = models.OneToOneField(
        SessaoMesa,
        on_delete=models.PROTECT,
        related_name='conta',
        verbose_name='Sessão',
    )
    valor_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Valor Total (R$)', validators=[MinValueValidator(Decimal('0.00'))],
    )
    meio_pagamento = models.CharField(
        max_length=10,
        choices=MEIO_PAGAMENTO_CHOICES,
        blank=True,
        default='',
        verbose_name='Meio de Pagamento',
    )
    pago = models.BooleanField(default=False, verbose_name='Pago')
    pago_em = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Pago em',
    )
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')

    class Meta:
        verbose_name = 'Conta'
        verbose_name_plural = 'Contas'
        ordering = ['-criado_em']
        constraints = [models.CheckConstraint(condition=models.Q(valor_total__gte=0), name='conta_total_valido')]

    def __str__(self):
        status = 'Pago' if self.pago else 'Em aberto'
        return f"Conta Mesa {self.sessao.mesa.numero} — R$ {self.valor_total} ({status})"

    def calcular_total(self):
        """Calcula o valor total somando todos os pedidos da sessão."""
        total = sum(
            pedido.valor_total
            for pedido in self.sessao.pedidos.exclude(status='CANCELADO')
        )
        self.valor_total = total
        return total
