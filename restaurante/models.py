from django.db import models
import uuid

class Mesa(models.Model):
    numero = models.IntegerField(unique=True, verbose_name="Número da Mesa")
    # UUID aleatório para garantir a segurança do QR Code (RNF05)
    token_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    ativa = models.BooleanField(default=True, verbose_name="Mesa Ativa")

    def __str__(self):
        return f"Mesa {self.numero}"

class Categoria(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    ordem = models.IntegerField(default=0, verbose_name="Ordem de Exibição")

    class Meta:
        ordering = ['ordem', 'nome']

    def __str__(self):
        return self.nome

class Produto(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='produtos')
    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    preco = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço (R$)")
    foto = models.ImageField(upload_to='produtos/', blank=True, null=True, verbose_name="Foto")
    disponivel = models.BooleanField(default=True, verbose_name="Disponível no Cardápio") # RF07

    def __str__(self):
        return f"{self.nome} - R$ {self.preco}"

class Adicional(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='adicionais')
    nome = models.CharField(max_length=100)
    preco = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço Adicional (R$)")

    def __str__(self):
        return f"{self.nome} (+R$ {self.preco})"

class Pedido(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('EM_PREPARO', 'Em Preparo'),
        ('PRONTO', 'Pronto'),
        ('ENTREGUE', 'Entregue'),
        ('CANCELADO', 'Cancelado'),
    ]

    mesa = models.ForeignKey(Mesa, on_delete=models.CASCADE, related_name='pedidos')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    observacao = models.TextField(blank=True, null=True, verbose_name="Observação Geral")

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ['-created_at']

    def __str__(self):
        return f"Pedido #{self.id} - Mesa {self.mesa.numero} ({self.get_status_display()})"


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='itens_pedido')
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço Unitário")
    adicionais = models.ManyToManyField(Adicional, blank=True, related_name='itens_pedido')
    observacao = models.CharField(max_length=255, blank=True, null=True, verbose_name="Observação do Item")

    class Meta:
        verbose_name = "Item do Pedido"
        verbose_name_plural = "Itens do Pedido"

    def __str__(self):
        return f"{self.quantidade}x {self.produto.nome} (Pedido #{self.pedido.id})"