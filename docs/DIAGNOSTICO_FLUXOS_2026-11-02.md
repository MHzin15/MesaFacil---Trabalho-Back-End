# Diagnóstico dos fluxos de atendimento

Este documento descreve o estado anterior às correções. A implementação atual
segue `COMANDAS_PRIVADAS.md` e `PATCHES_FLUXOS_ETAPA_1.md`: autoatendimento
com contas privadas por grupo e convite entre clientes, sem código nem aprovação
obrigatória da equipe.

Data: 02/11/2026. Análise do código local no commit 1332451 e documentação
pública de produtos do ramo. Não houve inspeção do banco de produção nem
alteração das regras de negócio neste diagnóstico.

## Comportamento atual

1. QR de mesa ativa, sem sessão: o cardápio abre para consulta. Adicionar e enviar
   pedidos depende da abertura da sessão pelo garçom ou administrador.
2. Abrir sessão libera pedidos para os clientes que acessam o QR da mesa.
3. Entregar um pedido não encerra a sessão. Vários pedidos acumulam na mesma conta.
4. Solicitar a conta apenas marca `conta_solicitada`; não fecha a sessão.
5. Confirmar o pagamento simulado registra o total como pago e encerra a sessão.
   Todos os pedidos precisam estar entregues ou cancelados.
6. Sessão sem valor a cobrar pode ser encerrada pela equipe sem pagamento.
7. O próximo grupo depende de uma nova sessão. O QR da mesa continua o mesmo.

## Achados e requisitos recomendados

### P0 — Navegador anterior pode entrar no atendimento seguinte

- Evidência: `security.vincular_mesa` substitui o vínculo pela sessão atual.
  `views.mesa_por_uuid` chama essa função e `cliente.js:refresh` consulta essa
  rota periodicamente, adotando o novo `sessao_id`.
- Cenário: grupo A sai, a equipe fecha a sessão e abre para B. O celular de A
  ainda aberto pode consultar a conta de B e enviar novos pedidos nessa sessão.
- Reproduzido com APIClient e CSRF válido: acesso inicialmente negado à nova
  conta; após o GET usado pelo polling, acesso 200 e criação de pedido 201.
- Requisito: vínculo do cliente específico por atendimento; encerramento revoga
  esse vínculo e não migra automaticamente o navegador para o próximo grupo.
  Separar consulta do estado da mesa de autorização para entrar na sessão.
- Um QR permanente é um localizador que pode ser fotografado ou salvo. Impedir a
  migração automática não basta: definir ingresso por código temporário,
  aprovação da equipe ou outro mecanismo por atendimento.
- Aceite: clientes de A não leem nem alteram B após pagamento e nova abertura,
  inclusive após polling, recarregar página e reutilizar o link salvo.

### P1 — Solicitação de conta e novos pedidos não têm política de fechamento

- Evidência: `services.pedir_conta` só marca um booleano; `services.criar` não
  verifica esse estado. Reprodução isolada confirmou criação 201 após solicitar.
- Risco: cliente adiciona itens durante a conferência e o total muda. Não é
  obrigatoriamente errado permitir consumo adicional, mas precisa ser explícito.
- Requisito: estado EM_FECHAMENTO bloqueia novos pedidos; ação explícita de
  retomar atendimento permite novo consumo e invalida a conferência anterior.
  Alternativamente, permitir pedidos e exigir nova conferência a cada alteração.

### P1 — Confirmação de pagamento não verifica o total conferido pelo operador

- Evidência: `PagamentoSerializer` recebe somente meio de pagamento; `pagar`
  recalcula o total vigente. Locks protegem a gravação, mas não validam o valor
  que o operador viu antes de confirmar.
- Risco: se a conta mudar antes da confirmação e as pendências já estiverem
  resolvidas, o backend pode marcar um total diferente daquele conferido.
- Requisito: enviar versão da conta e total conferido; se mudaram, rejeitar a
  confirmação e pedir nova revisão. O cálculo definitivo continua no servidor.
- O pagamento atual é explicitamente SIMULADO. Selecionar Pix/cartão não cobra
  nem confirma recebimento externo. Para uso real, definir confirmação manual de
  recebimento ou integração com provedor e estados próprios de pagamento.

### P1 — Falta tratamento autorizado de exceções após iniciar o preparo

- Evidência: transições permitem cancelamento apenas de RECEBIDO e o fechamento
  exige todos os pedidos entregues ou cancelados.
- Risco: item perdido, impróprio ou lançado errado após começar o preparo fica
  sem caminho correto de ajuste. Isso pode incentivar marcar entrega fictícia.
- Requisito: ajuste/cancelamento excepcional por gerente, com motivo, autor,
  horário e efeito financeiro. Tratar cancelamento de consumo e devolução de
  pagamento como operações diferentes, sem apagar o histórico.

### P2 — Abertura manual é um gargalo sem solicitação de atendimento

- Evidência: somente ADMIN/GARCOM abrem sessão; cliente fechado recebe orientação
  textual, sem chamado persistente para a equipe.
- Impacto: cliente lê QR e precisa localizar o garçom antes de poder pedir.
- Requisito: escolher política do restaurante: abertura pela equipe ao acomodar
  o grupo, solicitação digital de abertura ou abertura no primeiro pedido com
  controle de ingresso. A escolha deve ser configurável e proteger sessões.
- Não manter uma sessão permanente para vários grupos: mistura consumo e acesso.

### P2 — Pagamento e disponibilidade física da mesa estão acoplados

- Evidência: `pagar` encerra a sessão e `Mesa.status_display` considera livre toda
  mesa sem sessão ativa.
- Impacto: mesa paga aparece livre enquanto clientes ainda estão nela ou falta
  limpeza. Não há estado físico separado do financeiro.
- Requisito: distinguir atendimento encerrado, aguardando liberação/limpeza e
  mesa disponível. Novo atendimento sempre usa uma nova sessão.

### P2 — Fechamento limitado a uma conta e um meio de pagamento

- Evidência: `Conta` tem relação um-para-um com a sessão e um único meio; não há
  pagamentos parciais, saldo remanescente ou divisão por pessoa/item.
- Impacto: grupos e pagamento misto precisam de controles fora do sistema.
- Requisito: registros de pagamento associados à conta, saldo calculado e
  encerramento apenas após quitação; divisão sem duplicar itens ou cobrança.

### P2 — Não há transferência de mesa/comanda

- Evidência: não há operação de transferência no serviço ou na API analisados.
- Impacto: troca de mesa durante atendimento depende de contorno manual.
- Requisito: transferência autorizada e auditável, preservando consumo,
  pagamento, preparo e histórico; definir entrada dos clientes na mesa destino.

### P2 — Chamados e alertas dependem de acompanhar o painel

- Evidência: atualização visual por polling; não há chamado geral, confirmação
  de atendimento nem alerta sonoro/push nos scripts analisados. Polling deixa de
  atualizar enquanto a página está oculta.
- Impacto: pedido pronto ou fechamento solicitado pode esperar sem percepção da
  equipe. PWA instalada, sozinha, não garante notificação em segundo plano.
- Requisito: fila com horário, responsável e confirmação de atendimento; alertas
  visuais e sonoros opcionais. Push exige infraestrutura e permissão próprias.

## Fluxo recomendado

Mesa disponível → grupo acomodado → ingresso autorizado em nova sessão → pedidos
e entregas → solicitação de fechamento → conferência de versão/total → registro
de pagamentos → saldo quitado → encerramento e revogação dos acessos do grupo →
liberação/limpeza da mesa → disponível para nova sessão.

É uma proposta para este produto, não uma regra universal do setor. Manter a
restrição atual do garçom a acompanhamento e fechamento, conforme solicitado.

## Referências de produto

- [Cardápio Web — QR Code de Mesa](https://ajuda.cardapioweb.com/gestao/mesas-e-comandas/qr-code-de-mesa):
  abertura automática no primeiro pedido, sinalização da solicitação de conta
  com alerta sonoro e novo ciclo após fechamento.
- [Otter — Open Tabs](https://helpdesk.tryotter.com/hc/en-us/articles/11716604717331-Open-Tabs):
  consumo acumulado, configuração de pagamento antecipado ou ao final e divisão.
- [Toast — Split Checks](https://support.toasttab.com/en/article/Splitting-Checks-by-Item-1492811097734):
  divisão de contas e meios de pagamento com controle de permissão.
- [Toast — Transfer Items, Checks, and Payments](https://support.toasttab.com/en/article/Transferring-Items-Checks-and-Payments):
  transferência de itens, contas e pagamentos.
- [Toast — Void vs. Refund](https://support.toasttab.com/en/article/Understand-when-to-void-vs-refund?lang=en_US):
  distinção entre anular consumo e devolver um pagamento.

## Validação e limites

Dois testes temporários em `.tmp/test_diagnostico_fluxos.py` passaram reproduzindo
os achados de ingresso na sessão seguinte e envio após solicitação de conta.
São comprovações do comportamento atual, não testes de correção. Demais achados
derivam da leitura do código; não foi feita simulação de concorrência em
produção. Nenhuma correção funcional ou migração foi aplicada neste diagnóstico.
