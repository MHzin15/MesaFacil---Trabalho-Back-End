---

## 🤖 Prompt de Execução Integral do Marco 3 (API REST - Cardápio e Mesas)

> **Contexto para execução:** Atua como um desenvolvedor Back-End especialista em Django e Django REST Framework (DRF). Preciso que implementes a API REST inicial do projeto "MesaFácil" (Marco 3), permitindo a comunicação JSON para o front-end, seguindo as etapas abaixo:

### 1. Instalação de Dependências e Configuração de CORS
- Adicionar ao `requirements.txt` e instalar as bibliotecas `djangorestframework` e `django-cors-headers`.
- Registar `'rest_framework'` e `'corsheaders'` em `INSTALLED_APPS` no `settings.py`.
- Configurar o middleware `corsheaders.middleware.CorsMiddleware` e liberar permissões de origem via `CORS_ALLOW_ALL_ORIGINS = True` para ambiente de desenvolvimento.

### 2. Criação de Serializers (`restaurante/serializers.py`)
- Criar a camada de serialização utilizando `serializers.ModelSerializer` para mapear todos os campos dos modelos:
  - `CategoriaSerializer`
  - `AdicionalSerializer`
  - `ProdutoSerializer`
  - `MesaSerializer`

### 3. Implementação dos ViewSets (`restaurante/views.py`)
- Criar a camada de controllers utilizando `viewsets.ModelViewSet` para disponibilizar automaticamente as rotas de CRUD completo (GET, POST, PUT, PATCH, DELETE) para os recursos de Categorias, Adicionais, Produtos e Mesas.

### 4. Roteamento de URLs (`restaurante/urls.py` e `mesafacil/urls.py`)
- Configurar o `DefaultRouter` do DRF na app `restaurante` registando os prefixos `/categorias`, `/adicionais`, `/produtos` e `/mesas`.
- Incluir o roteamento da app sob a rota raiz `/api/` no ficheiro principal de URLs do projeto.
- Validar o funcionamento através da interface navegável do Django REST Framework.