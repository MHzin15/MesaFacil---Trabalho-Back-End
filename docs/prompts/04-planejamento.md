---

## 🤖 Prompt de Execução Integral do Marco 4 (Módulo de Pedidos e Carrinho)

> **Contexto para execução:** Atua como um desenvolvedor Back-End especialista em Django e Django REST Framework (DRF). Preciso que implementes o módulo de Pedidos e Carrinho do projeto "MesaFácil" (Marco 4), permitindo a criação de comandas associadas às mesas e itens detalhados, seguindo as etapas abaixo:

### 1. Modelação de Dados (`restaurante/models.py`)
- Criar o modelo `Pedido` com os campos: `mesa` (ForeignKey), `created_at`, `updated_at`, `status` (Choices: PENDENTE, EM_PREPARO, PRONTO, ENTREGUE, CANCELADO) e `observacao`.
- Criar o modelo `ItemPedido` com os campos: `pedido` (ForeignKey), `produto` (ForeignKey), `quantidade`, `preco_unitario`, `adicionais` (ManyToManyField) e `observacao`.
- Executar `makemigrations` e `migrate` para atualizar a base de dados PostgreSQL.

### 2. Registo no Painel Administrativo (`restaurante/admin.py`)
- Configurar `ItemPedidoInline` (TabularInline) para permitir a adição rápida de itens diretamente na interface do pedido.
- Registar `PedidoAdmin` com filtros por status e data, barra de pesquisa e visualização em tabela.

### 3. Serializadores (`restaurante/serializers.py`)
- Criar `ItemPedidoSerializer` com o campo legível `produto_nome`.
- Criar `PedidoSerializer` com o campo legível `mesa_numero` e listagem aninhada dos itens (`itens` com `many=True`).

### 4. ViewSets e Roteamento (`restaurante/views.py` e `restaurante/urls.py`)
- Implementar `PedidoViewSet` e `ItemPedidoViewSet` utilizando `viewsets.ModelViewSet`.
- Registar os endpoints `/pedidos/` e `/itens-pedido/` no `DefaultRouter` do DRF.