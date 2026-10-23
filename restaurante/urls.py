from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'categorias', views.CategoriaViewSet)
router.register(r'produtos', views.ProdutoViewSet)
router.register(r'adicionais', views.AdicionalViewSet)
router.register(r'mesas', views.MesaViewSet)
router.register(r'sessoes', views.SessaoMesaViewSet)

urlpatterns = [
    # Router padrão (CRUD)
    path('', include(router.urls)),

    # Cardápio público
    path('cardapio/', views.cardapio, name='cardapio'),

    # Mesa via QR Code (UUID)
    path('mesa/<uuid:uuid>/', views.mesa_por_uuid, name='mesa-por-uuid'),

    # Sessão da Mesa
    path('mesas/<int:mesa_id>/abrir-sessao/', views.abrir_sessao, name='abrir-sessao'),
    path('sessoes/<int:sessao_id>/fechar/', views.fechar_sessao, name='fechar-sessao'),

    # Pedidos
    path('pedidos/criar/', views.criar_pedido, name='criar-pedido'),
    path('pedidos/<int:pedido_id>/status/', views.alterar_status_pedido, name='alterar-status-pedido'),
    path('mesa/<uuid:uuid>/pedidos/', views.pedidos_da_mesa, name='pedidos-da-mesa'),

    # Painel da Cozinha
    path('cozinha/', views.painel_cozinha, name='painel-cozinha'),
    path('produtos/<int:produto_id>/disponibilidade/', views.marcar_disponibilidade_produto, name='disponibilidade-produto'),

    # Painel do Garçom
    path('garcom/', views.painel_garcom, name='painel-garcom'),
    path('garcom/mapa-mesas/', views.mapa_mesas, name='mapa-mesas'),

    # Conta e Pagamento
    path('mesa/<uuid:uuid>/conta/', views.ver_conta, name='ver-conta'),
    path('mesa/<uuid:uuid>/solicitar-conta/', views.solicitar_conta, name='solicitar-conta'),
    path('sessoes/<int:sessao_id>/pagamento/', views.processar_pagamento, name='processar-pagamento'),

    # Administração
    path('admin/pedidos/', views.consultar_pedidos, name='consultar-pedidos'),
    path('admin/contas/', views.consultar_contas, name='consultar-contas'),

    # Autenticação
    path('auth/usuario/', views.usuario_atual, name='usuario-atual'),
]
