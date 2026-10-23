# MesaFácil 🍽️📱

O **MesaFácil** é uma aplicação web progressiva (PWA) desenvolvida em Django para gerir pedidos
através de QR Code em restaurantes. O sistema elimina a necessidade de o garçom anotar os pedidos
manualmente, permitindo que o cliente escaneie o QR Code da mesa, consulte o cardápio, monte o
pedido, envie-o diretamente para a cozinha e acompanhe o status em tempo real até o fechamento
da conta.

## 🛠️ Tecnologias Utilizadas

| Camada | Tecnologia |
|--------|-----------|
| Linguagem | Python 3 |
| Framework | Django 5.2 |
| API REST | Django REST Framework |
| Banco de Dados | PostgreSQL (psycopg v3) |
| QR Code | qrcode + Pillow |
| Documentação API | drf-spectacular (Swagger/OpenAPI) |
| Filtros | django-filter |
| Frontend | HTML5, CSS3, Bootstrap 5, JavaScript (Fetch API) |
| PWA | manifest.json, Service Worker, Cache API |
| Arquivos Estáticos | WhiteNoise |
| Testes | pytest + pytest-django |

## 👥 Divisão de Tarefas

* **Membro 1 (Backend & Banco de Dados):** Modelação de dados (Django ORM), API REST,
  autenticação, lógica de sessões de mesa e painéis de controlo.
* **Membro 2 (Frontend, PWA & UX):** Interfaces mobile-first (Cliente), painéis responsivos
  (Cozinha/Garçom), integração via Fetch API, Service Worker e testes automatizados.

## 🚀 Como Executar o Projeto

### Pré-requisitos

- Python 3.11+
- PostgreSQL 15+
- Git

### 1. Clonar o repositório

```bash
git clone https://github.com/MHzin15/MesaFacil---Trabalho-Back-End.git
cd MesaFacil---Trabalho-Back-End
```

### 2. Criar ambiente virtual e instalar dependências

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente

Copie o arquivo `.env.example` para `.env` e ajuste os valores:

```bash
cp .env.example .env
```

Edite o `.env` com as credenciais do seu PostgreSQL:

```
DEBUG=True
SECRET_KEY=sua-chave-secreta-aqui
DATABASE_URL=postgres://postgres:sua_senha@localhost:5432/mesa_facil
ALLOWED_HOSTS=127.0.0.1,localhost
```

### 4. Criar o banco de dados

```bash
# No terminal do PostgreSQL (psql):
CREATE DATABASE mesa_facil;
```

### 5. Executar migrations

```bash
python manage.py migrate
```

### 6. Carregar dados de exemplo

```bash
python manage.py seed_data
```

Isso cria:
- 10 mesas
- Cardápio completo com 6 categorias e 15 produtos com adicionais
- Usuários de teste (veja abaixo)

### 7. Rodar o servidor

```bash
python manage.py runserver
```

Acesse:
- **API:** http://localhost:8000/api/
- **Documentação Swagger:** http://localhost:8000/api/docs/
- **Admin Django:** http://localhost:8000/admin/

## 👤 Usuários de Teste

| Usuário | Senha | Perfil |
|---------|-------|--------|
| `admin` | `admin123` | Administrador |
| `cozinha` | `cozinha123` | Cozinha |
| `garcom` | `garcom123` | Garçom |

## 📡 Endpoints da API

### Públicos (sem login)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/cardapio/` | Cardápio completo agrupado por categorias |
| GET | `/api/mesa/<uuid>/` | Dados da mesa pelo QR Code (UUID) |
| POST | `/api/pedidos/criar/` | Enviar um pedido |
| GET | `/api/mesa/<uuid>/pedidos/` | Acompanhar pedidos da mesa |
| GET | `/api/mesa/<uuid>/conta/` | Ver conta da mesa |
| POST | `/api/mesa/<uuid>/solicitar-conta/` | Solicitar fechamento da conta |

### Cozinha (login obrigatório)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/cozinha/` | Pedidos agrupados por status |
| PATCH | `/api/pedidos/<id>/status/` | Alterar status do pedido |
| PATCH | `/api/produtos/<id>/disponibilidade/` | Marcar produto indisponível |

### Garçom (login obrigatório)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/garcom/` | Pedidos prontos + mesas aguardando conta |
| GET | `/api/garcom/mapa-mesas/` | Situação de todas as mesas |
| POST | `/api/mesas/<id>/abrir-sessao/` | Abrir sessão de uma mesa |
| POST | `/api/sessoes/<id>/fechar/` | Fechar sessão |
| POST | `/api/sessoes/<id>/pagamento/` | Processar pagamento simulado |

### Administração (login obrigatório)
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/admin/pedidos/` | Consultar pedidos (filtros por data) |
| GET | `/api/admin/contas/` | Consultar contas fechadas |
| POST | `/api/mesas/<id>/gerar-qrcode/` | Gerar QR Code da mesa |

### Documentação Interativa
| URL | Descrição |
|-----|-----------|
| `/api/docs/` | Swagger UI |
| `/api/redoc/` | ReDoc |
| `/api/schema/` | Schema OpenAPI (JSON) |

## 🧪 Executar Testes

```bash
python -m pytest -q
# Alternativa com o runner do Django:
python manage.py test restaurante
```

Os testes usam SQLite em memória, com migrations reais e isolamento por teste.
Não exigem PostgreSQL em execução, `.env` ou carga prévia de `seed_data`.
Cobrem RN01–RN08, RNF08 e as respostas do painel da cozinha, incluindo as 36
combinações de status, auditoria, rollback, permissões e atualização por polling.
Os cenários estão detalhados em [docs/prompts/06-marco3-pedidos-e-testes.md](docs/prompts/06-marco3-pedidos-e-testes.md).

Após atualizar uma instalação existente, execute `python manage.py migrate`
para aplicar a restrição de uma sessão ativa por mesa (`0002_sessao_ativa_unica`).

## 📁 Estrutura do Projeto

```
MesaFácil/
├── core/                  # Configurações do projeto Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── restaurante/           # App principal
│   ├── management/
│   │   └── commands/
│   │       └── seed_data.py    # Dados de exemplo
│   ├── migrations/
│   ├── admin.py           # Admin customizado
│   ├── models.py          # Modelos de dados
│   ├── permissions.py     # Permissões por perfil
│   ├── serializers.py     # Serializers da API
│   ├── urls.py            # Rotas da API
│   └── views.py           # Views / lógica de negócio
├── docs/
│   ├── esboco-telas.md
│   └── prompts/           # Histórico de prompts de IA
├── static/                # Arquivos estáticos
├── templates/             # Templates HTML
├── .env.example
├── .gitignore
├── manage.py
├── pytest.ini
├── requirements.txt
└── README.md
```
