# Marco 3 — Carrinho, cliente e cozinha

Contexto: a API e os 39 testes de regras já existem. As orientações oficiais exigem
telas reais e atualização sem recarregar; respostas REST isoladas não concluem o marco.

Prompt adaptado: implementar em Django templates, Bootstrap 5 local e Fetch API as
telas da mesa e da cozinha. Permitir selecionar extras, quantidade, observações,
editar/remover itens, revisar e confirmar. Exibir os pedidos da sessão e consultar
o status a cada quatro segundos. Cozinha deve agrupar os pedidos, permitir preparo
e alterar disponibilidade. Não adicionar frameworks ou serviços de hospedagem.

Critérios: identidade da mesa por UUID, validação definitiva de preços no servidor,
mensagens de erro, proteção das páginas por login/perfil, saída por POST com CSRF,
layout para celular e monitor, escape de conteúdo recebido pela API.

Revisão: incluído o storage de arquivos de mídia, ausente na configuração anterior,
para que uploads e QR Codes não falhem. Testes de páginas verificam renderização,
permissões, mesa inativa e logout. Bootstrap 5.3.8 servido localmente, conforme a
[distribuição oficial](https://getbootstrap.com/docs/5.3/getting-started/download/).
