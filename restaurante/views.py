from rest_framework import viewsets
from .models import Mesa, Categoria, Produto, Adicional, Pedido, ItemPedido
from .serializers import (
    MesaSerializer, 
    CategoriaSerializer, 
    ProdutoSerializer, 
    AdicionalSerializer,
    PedidoSerializer,
    ItemPedidoSerializer
)

class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer

class AdicionalViewSet(viewsets.ModelViewSet):
    queryset = Adicional.objects.all()
    serializer_class = AdicionalSerializer

class ProdutoViewSet(viewsets.ModelViewSet):
    queryset = Produto.objects.all()
    serializer_class = ProdutoSerializer

class MesaViewSet(viewsets.ModelViewSet):
    queryset = Mesa.objects.all()
    serializer_class = MesaSerializer

class PedidoViewSet(viewsets.ModelViewSet):
    queryset = Pedido.objects.all()
    serializer_class = PedidoSerializer

class ItemPedidoViewSet(viewsets.ModelViewSet):
    queryset = ItemPedido.objects.all()
    serializer_class = ItemPedidoSerializer