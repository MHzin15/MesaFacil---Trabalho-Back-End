from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoriaViewSet, AdicionalViewSet, ProdutoViewSet, MesaViewSet, PedidoViewSet, ItemPedidoViewSet

router = DefaultRouter()
router.register(r'categorias', CategoriaViewSet)
router.register(r'adicionais', AdicionalViewSet)
router.register(r'produtos', ProdutoViewSet)
router.register(r'mesas', MesaViewSet)
router.register(r'pedidos', PedidoViewSet)
router.register(r'itens-pedido', ItemPedidoViewSet)

urlpatterns = [
    path('', include(router.urls)),
]