# Acompanhamento da mesa pelo garçom

## Permissões e navegação

- **Risco original:** o garçom acessava controles destinados ao cliente e podia
  criar pedidos, inclusive diretamente pela API.
- **Solução aplicada:** bloqueio por perfil na API e no serviço transacional,
  navegação de acompanhamento e redirecionamento do carrinho.
- **Impacto:** a autorização passa a valer também fora da interface, sem mudança
  no esquema do banco ou no fluxo de pedido do cliente.

- Usuários com perfil GARCOM consultam o cardápio, os pedidos e as contas da mesa.
  O carrinho e os formulários de criação não são renderizados para esse perfil.
  A URL antiga de carrinho redireciona para os pedidos da mesma mesa.
- A API de criação e o serviço transacional rejeitam novos pedidos enviados pelo
  perfil GARCOM com erro de permissão, inclusive tentativas fora da interface.
  Cliente sem login continua utilizando o fluxo de pedido existente.
- A navegação do garçom usa “Pedidos” e “Contas”, com textos de acompanhamento.

## Apresentação dos pedidos

- **Problema original:** o aviso de atualização ocupava espaço e cartões com
  conteúdos diferentes desalinhavam totais e andamento.
- **Solução aplicada:** remoção do aviso e grade com cartões de mesma altura,
  preservando todo o conteúdo.
- **Impacto:** renderização compartilhada reduz duplicação; a frequência de
  atualização e as regras dos pedidos permanecem iguais.

- O aviso de atualização a cada quatro segundos foi removido da apresentação.
  A atualização dos dados continua automática.
- Os cartões de pedido compartilham uma renderização entre cliente e garçom;
  a grade e o layout interno alinham altura, totais e andamento, sem cortar itens.

## Acesso ao fechamento

- **Problema original:** o próprio garçom recebia a mensagem de que seria avisado
  e precisava voltar ao painel para encontrar o fechamento solicitado.
- **Solução aplicada:** mensagem contextual e botão para a tela de contas quando
  a mesa solicitou o fechamento.
- **Impacto:** menos passos de navegação, usando o fluxo de fechamento existente.

- Quando o fechamento foi solicitado, o garçom vê “Ir para fechamento de contas”
  apontando para `/garcom/contas/`, em vez da mensagem dirigida ao cliente.
- Não houve alteração nas regras de preparo, entrega ou pagamento.

Validação: 137 testes aprovados no SQLite, seis ignorados por exigirem PostgreSQL
e 158 subtestes aprovados. As regressões adicionais cobrem o bloqueio na API e
no serviço, a navegação sem carrinho e a criação de pedidos pelo cliente.
Também foram conferidos no navegador o alinhamento de pedidos com quantidades
diferentes de itens, o atalho de fechamento e a apresentação do cliente.
