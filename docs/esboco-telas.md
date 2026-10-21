# 🎨 Esboço das Telas (Wireframes Conceituais) — MesaFácil

Este documento descreve a estrutura visual e de experiência do utilizador (UX/UI) das interfaces do **MesaFácil**, abrangendo os perfis de **Cliente**, **Cozinha** e **Garçom**.

---

## 📱 1. Interface do Cliente (Mobile-First — PWA)

A interface do cliente é desenhada especificamente para smartphones, sem necessidade de criação de conta ou login.

### 1.1. Tela do Cardápio
* **Cabeçalho (Header):**
  * Identificação visual da mesa (ex: `Mesa 04`).
  * Indicador de estado de ligação (Online / Offline com alerta amigável de cache).
  * Ícone do Carrinho com contador de itens em tempo real.
* **Carrossel de Categorias:**
  * Barra de navegação horizontal com botões/abas (*Entradas, Pratos Principais, Bebidas, Sobremesas*).
* **Lista de Produtos (Grelha/Cards):**
  * Imagem do produto.
  * Nome do produto e descrição curta.
  * Preço formatado no padrão brasileiro (ex: `R$ 41,90`).
  * Botão "+ Adicionar".
  * *Produtos indisponíveis:* Aparecem esmaecidos (desabilitados) com a tag "Indisponível".

### 1.2. Modal / Tela do Item
* Imagem destacada do produto.
* Seletor de quantidade (`-` `1` `+`).
* Listagem de **Adicionais** disponíveis (com caixas de seleção e o respetivo valor extra).
* Campo de texto livre para **Observações** (ex: *"Sem cebola", "Ponto do hambúrguer: ao ponto"*).
* Botão principal: "Adicionar ao Carrinho - R$ XX,XX" (com cálculo do valor parcial).

### 1.3. Tela do Carrinho & Revisão
* Lista de todos os itens escolhidos com os respetivos adicionais e observações.
* Opção de alterar quantidade ou remover itens do carrinho.
* Resumo financeiro: Subtotal por item e Valor Total do Pedido.
* Botão de ação: "Confirmar e Enviar Pedido para a Cozinha".

### 1.4. Acompanhamento do Pedido (Status)
* Linha do tempo visual do estado dos pedidos da sessão:
  `[ Recebido ] ➔ [ Em Preparação ] ➔ [ Pronto ] ➔ [ A caminho ] ➔ [ Entregue ]`
* Histórico de todos os pedidos já enviados pela mesa na sessão atual.

### 1.5. Extrato & Fechamento da Conta
* Resumo consolidado da conta da mesa (soma de todos os pedidos confirmados e entregues).
* Botão "Pedir a Conta".
* Seleção do meio de pagamento simulado (*Pix, Cartão ou Dinheiro*).
* Confirmação visual de pagamento aprovado e encerramento da sessão da mesa.

---

## 🖥️ 2. Painel da Cozinha (Tablet / Monitor — PWA)

Interface otimizada para ecrãs maiores, focada na agilidade operacional e atualização automática sem recarregar a página (polling).

### 2.1. Visualização Principal (Formato Kanban / Grid)
* **Colunas de Estado:**
  * **Recebidos:** Novas solicitações enviadas pelos clientes.
  * **Em Preparação:** Pedidos aceites e a serem confecionados.
  * **Prontos:** Pedidos finalizados aguardando que o garçom os leve à mesa.

### 2.2. Cartão de Pedido (Card de Cozinha)
* **Cabeçalho do Card:** Número da Mesa (em destaque) + Horário do envio (ex: `Mesa 02 — 19:42`).
* **Corpo do Card:**
  * Lista de itens e quantidades.
  * Destaque visual colorido para **Adicionais** e **Observações do cliente**.
* **Rodapé de Ações:**
  * Botão "Aceitar / Iniciar Preparo" (avança de *Recebido* para *Em Preparação*).
  * Botão "Marcar como Pronto" (avança de *Em Preparação* para *Pronto*).

### 2.3. Gestão Rápida de Disponibilidade
* Botão/Atalho de acesso rápido para alternar a disponibilidade de qualquer produto do cardápio em tempo real (ex: marcar um ingrediente como esgotado).

---

## 📋 3. Painel do Garçom (Mobile / Tablet — PWA)

Interface focada no atendimento presencial, controlo de mesas e entregas de pedidos. Exige login de utilizador da equipa.

### 3.1. Visão Geral do Salão (Mapa de Mesas)
* Grelha visual de cartões representando as mesas cadastradas no restaurante.
* **Indicadores de Estado por Cores:**
  * 🟩 **Livre:** Pronta para receber clientes.
  * 🟥 **Ocupada:** Possui sessão aberta e consumo em andamento.
  * 🟨 **Aguardando Conta:** Cliente solicitou o encerramento da conta.
* Botão para "Abrir Sessão" e "Fechar Sessão / Liberar Mesa".

### 3.2. Painel de Entregas (Pedidos Prontos)
* Notificações de pedidos com estado **Pronto** vindos da cozinha.
* Ações do Garçom:
  * Botão "A caminho" (indica que o pedido saiu da cozinha).
  * Botão "Entregue" (confirma a entrega na mesa).

### 3.3. Painel de Solicitções de Conta
* Alertas das mesas que pediram a conta.
* Opção para o garçom rever o valor total consolidado e confirmar o fechamento presencialmente ou validar o pagamento simulado.