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
