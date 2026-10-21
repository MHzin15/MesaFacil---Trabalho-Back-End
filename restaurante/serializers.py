from rest_framework import serializers
from .models import Mesa, Categoria, Produto, Adicional

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'

class AdicionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Adicional
        fields = '__all__'

class ProdutoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Produto
        fields = '__all__'

class MesaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mesa
        fields = '__all__'