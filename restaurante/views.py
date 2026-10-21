from django.shortcuts import render
from rest_framework import viewsets
from .models import Mesa, Categoria, Produto, Adicional
from .serializers import (
    MesaSerializer, 
    CategoriaSerializer, 
    ProdutoSerializer, 
    AdicionalSerializer
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
