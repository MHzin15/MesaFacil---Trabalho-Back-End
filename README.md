# MesaFácil 🍽️📱

O **MesaFácil** é uma aplicação web progressiva (PWA) desenvolvida em Django para gerir pedidos através de QR Code em restaurantes[cite: 1]. O sistema elimina a necessidade de o garçom anotar os pedidos manualmente, permitindo que o cliente escaneie o QR Code da mesa, consulte o cardápio, monte o pedido, envie-o diretamente para a cozinha e acompanhe o estado em tempo real até ao fechamento da conta[cite: 1].

## 🛠️ Tecnologias Utilizadas (Stack)
* **Linguagem:** Python 3
* **Framework Backend:** Django & Django REST Framework (DRF)[cite: 4]
* **Base de Dados:** PostgreSQL (com driver `psycopg` v3)[cite: 4]
* **Geração de QR Codes:** `qrcode` (com Pillow)[cite: 4]
* **Frontend:** HTML5, CSS3, Bootstrap 5, JavaScript (Fetch API)[cite: 4]
* **PWA:** Manifest.json, Service Worker, Cache API[cite: 4]

## 👥 Divisão de Tarefas da Dupla
* **Membro 1 (Backend & Base de Dados):** Modelação de dados (Django ORM), configuração da API REST, autenticação, lógica de sessões de mesa e painéis de controlo.
* **Membro 2 (Frontend, PWA & UX):** Desenvolvimento das interfaces mobile-first (Cliente), painéis responsivos (Cozinha/Garçom), integração via Fetch API, Service Worker e testes automatizados.

## 🚀 Como Executar o Projeto
Instruções detalhadas serão adicionadas nos próximos marcos conforme o desenvolvimento avança (seguindo as diretrizes do RNF12).