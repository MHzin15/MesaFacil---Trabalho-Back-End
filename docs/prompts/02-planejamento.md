# Registo de Prompt e Planeamento — Marco 2: Base e Cardápio

## 🎯 Objetivo do Marco
Configurar a conexão segura com a base de dados PostgreSQL utilizando variáveis de ambiente (`.env`), criar a aplicação principal `restaurante` e implementar os modelos de dados (*Models*) para as Mesas (com UUID para QR Code) e para o Cardápio (Categorias, Produtos e Adicionais), além do registo no Django Admin.

## 🛠️ Tecnologias e Dependências Utilizadas
- **Django 5.2** e **Django REST Framework**
- **PostgreSQL** com driver `psycopg[binary]`
- **django-environ** para gestão segura de variáveis de ambiente (`.env` e `.env.example`)
- **Pillow** para suporte a imagens de produtos (`ImageField`)

## 📝 Passos Executados
1. **Configuração de Ambiente:** Criação dos ficheiros `.env` e `.env.example` protegendo a `SECRET_KEY` e as credenciais de acesso ao PostgreSQL (`DATABASE_URL`).
2. **Atualização do `settings.py`:** Configuração do idioma para Português do Brasil (`pt-br`), fuso horário (`America/Sao_Paulo`), diretórios de ficheiros estáticos/mídia e integração com o `django-environ`.
3. **Criação da App `restaurante`:** Estruturação da aplicação modular no projeto.
4. **Modelação de Dados (`models.py`):**
   - `Mesa`: Número único, campo `ativa` e `token_uuid` (UUID aleatório para segurança do QR Code - RNF05).
   - `Categoria`: Nome e ordenação de exibição.
   - `Produto`: Relação com Categoria, nome, descrição, preço, foto e status de disponibilidade (`disponivel` - RF07).
   - `Adicional`: Relação com Produto, nome e preço adicional.
5. **Configuração do Painel Administrativo (`admin.py`):** Registo e customização da visualização dos modelos no Django Admin para gestão por parte do restaurante (RF23).
6. **Migrações:** Execução bem-sucedida de `makemigrations` e `migrate` para a base de dados PostgreSQL (`mesa_facil`).

## 🚀 Próximos Passos
- Criação do utilizador administrador (`createsuperuser`).
- Inserção de dados iniciais de teste (categorias, produtos e mesas).
- Desenvolvimento dos *Serializers* e *Views* (API REST) para a listagem do cardápio e gestão de pedidos.