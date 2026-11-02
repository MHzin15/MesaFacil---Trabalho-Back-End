from django.urls import path
from . import views

app_name = 'gestao'
urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('equipe/', views.funcionarios, name='equipe'),
    path('equipe/novo/', views.funcionario_editar, name='funcionario-novo'),
    path('equipe/<int:pk>/', views.funcionario_editar, name='funcionario'),
    path('equipe/<int:pk>/senha/', views.senha, name='senha'),
    path('mesas/', views.mesas, name='mesas'),
    path('mesas/<int:pk>/abrir/', views.abrir_mesa, name='abrir-mesa'),
    path('cardapio/', views.cardapio, name='cardapio'),
    path('cardapio/<int:pk>/preco/', views.preco, name='preco'),
    path('cardapio/<int:pk>/disponibilidade/', views.disponibilidade, name='disponibilidade'),
    path('categorias/', views.categorias, name='categorias'),
    path('adicionais/', views.adicionais, name='adicionais'),
    path('cadastro/<str:tipo>/novo/', views.cadastro, name='cadastro-novo'),
    path('cadastro/<str:tipo>/<int:pk>/', views.cadastro, name='cadastro'),
    path('pedidos/', views.pedidos, name='pedidos'),
    path('pedidos/<int:pk>/', views.pedido, name='pedido'),
    path('pedidos/<int:pk>/cancelar/', views.cancelar, name='cancelar'),
    path('relatorios/', views.relatorios, name='relatorios'),
    path('atividades/', views.atividades, name='atividades'),
]
