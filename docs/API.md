# Contrato e integração da API

OpenAPI completo: [openapi.yaml](openapi.yaml); Swagger em `/api/docs/` e ReDoc
em `/api/redoc/`. Para regenerar: `python manage.py spectacular --file docs/openapi.yaml --validate --fail-on-warn`.

## Cliente sem login

1. Abra o QR `/mesa/<UUID>/` ou consulte `GET /api/mesa/<UUID>/` com cookies habilitados.
   A resposta identifica a mesa e a sessão ativa; o servidor estabelece o contexto
   na sessão anônima e envia o cookie `csrftoken`.
2. Nas escritas, envie esse valor em `X-CSRFToken`, com `credentials: same-origin`.
3. Leia `/api/cardapio/`; envie `/api/pedidos/criar/` com `mesa_uuid`, `sessao_id`,
   `itens`, `total_esperado` e, preferencialmente, `chave_envio` (UUID gerado por tentativa).
4. Cada item contém `produto_id`, `quantidade` (1–99), `adicionais_ids` sem repetição
   e `observacao` de até 255 caracteres. Um pedido aceita até 100 itens.
5. Reutilize a mesma chave e o mesmo conteúdo se a resposta se perder. O servidor
   retorna o pedido original; reutilizar a chave com outro conteúdo é rejeitado.
   Uma nova intenção de pedido usa outra chave.
6. Consulte `/api/mesa/<UUID>/pedidos/` e `/conta/` por polling, em intervalos de
   quatro segundos. O primeiro sempre retorna uma lista. Cancelados aparecem na
   conta, mas não entram no total devido.
7. Solicite a conta com POST `/api/mesa/<UUID>/solicitar-conta/`. Isso não encerra
   o atendimento nem permite pagamento enquanto houver pedidos pendentes.

O servidor ignora preços e status enviados pelo cliente e grava snapshots dos
preços do catálogo. Valores monetários no JSON são strings com duas casas decimais.
IDs numéricos e o contexto de outra mesa não autorizam acesso. Após fechamento ou
reabertura, atualize o contexto pelo QR; um pedido antigo não entra na sessão nova.

## Equipe

Login em `/entrar/`. Cozinha/admin consultam `/api/cozinha/`, alteram disponibilidade
e avançam preparo. Garçom/admin consultam `/api/garcom/`, `/api/garcom/mapa-mesas/`,
abrem sessões, avançam entrega e confirmam pagamento. Todos exigem perfil correto.
As transições válidas e permissões são verificadas novamente pelo serviço.

Garçom/admin consultam GET `/api/sessoes/<id>/conta/` e solicitam a conta com
POST `/api/sessoes/<id>/solicitar-conta/`, sem usar o contexto anônimo do cliente.
O pagamento usa POST `/api/sessoes/<id>/pagamento/` com `meio_pagamento` igual a
PIX, CARTAO ou DINHEIRO. Se aprovado, a sessão fecha na mesma transação.
POST `/api/sessoes/<id>/fechar/` serve para sessão sem cobrança e sem pendências.

Admin consulta `/api/admin/pedidos/` e `/api/admin/contas/` por `data_inicio` e
`data_fim` no formato YYYY-MM-DD; pedidos também aceitam `status`. Entradas inválidas
retornam 400. A consulta de contas é limitada a contas pagas.

QR privado: GET `/api/mesas/<id>/qr-code/`, perfil ADMIN. A ação POST
`/api/mesas/<id>/gerar_qrcode/` retorna links, sem persistir PNG em mídia pública.

Respostas de pedidos, contas e equipe têm `Cache-Control: no-store`. Apenas
cardápio e recursos públicos podem ser candidatos ao cache offline do PWA.

O frontend envia `total_esperado` como valor de confirmação: o servidor compara
com seu próprio cálculo e rejeita divergências, sem aceitar esse campo como preço.
Na API ele é opcional para compatibilidade; no cliente do projeto é sempre enviado.
