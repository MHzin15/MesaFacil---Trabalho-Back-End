# Fluxos de atendimento — primeira etapa

Implementação das prioridades crítica e alta do diagnóstico de 02/11/2026.

| Prioridade | Problema identificado | Melhoria aplicada | Estado |
| --- | --- | --- | --- |
| Crítica | Cliente anterior podia ingressar na sessão seguinte pelo polling | Comanda privada por grupo, com convite explícito entre familiares | Implementado |
| Alta | Novos pedidos durante conferência de conta | Bloqueio no servidor e na interface; retomada explícita pela equipe | Implementado |
| Alta | Pagamento sem validar o total conferido | Total e versão obrigatórios, com rejeição de conferência desatualizada | Implementado |
| Alta | Ausência de exceção após iniciar preparo | Cancelamento excepcional pelo administrador, com justificativa e auditoria | Implementado |
| Média | Cliente depende de localizar o garçom para abrir mesa | Primeiro pedido válido abre a sessão automaticamente | Implementado |
| Média | Pagamento torna mesa fisicamente disponível | Separar situação financeira e liberação/limpeza | Próxima etapa |
| Média | Uma conta e um meio de pagamento | Pagamentos parciais e divisão de conta | Próxima etapa |
| Média | Troca de mesa sem operação própria | Transferência autorizada com histórico | Próxima etapa |
| Média | Avisos dependem do painel aberto | Fila de chamados com responsável e alertas | Próxima etapa |

## 1. Autoatendimento e comandas privadas

- **Risco original:** o QR da mesa permitia entrar na conta de outro grupo.
- **Solução final:** cada navegador começa um rascunho privado. O primeiro pedido
  cria uma comanda independente. Para consumir na mesma conta, os familiares
  entram por convite enviado pelo próprio cliente, com QR ou link de 15 minutos.
  Abrir o QR da mesa, recarregar ou iniciar outra visita não concede contas alheias.
- **Impacto:** várias comandas podem ficar abertas na mesma mesa. Pagamento e
  bloqueio de pedidos no fechamento atingem somente a comanda selecionada.
  Não há código digitado, cadastro ou aprovação obrigatória do garçom.
- As regras finais, migrações, testes e limites estão em `COMANDAS_PRIVADAS.md`.

## 2. Fechamento e retomada do consumo

- **Risco original:** solicitar a conta não impedia novas despesas durante a
  conferência do garçom.
- **Solução aplicada:** a solicitação passa a bloquear pedidos novos na API e no
  serviço. O cliente vê um aviso e os controles de pedido ficam desabilitados.
  O garçom/administrador pode usar “Retomar atendimento e liberar pedidos”. Essa
  ação mantém a sessão existente e invalida a conferência financeira anterior.
  Reenvio com a mesma chave de um pedido já recebido continua retornando o pedido
  original, inclusive durante o fechamento, sem criar outro nem cobrar duas vezes.
- **Impacto:** reutiliza `conta_solicitada` como estado de fechamento. Nenhuma
  mudança nas etapas normais de preparo ou entrega. Retomadas ficam auditadas.

## 3. Total e versão na confirmação de pagamento

- **Risco original:** o servidor podia registrar como pago um total diferente do
  conferido na tela, mesmo mantendo integridade transacional.
- **Solução aplicada:** o pagamento exige `total_esperado` e `versao_conta`.
  Pedidos novos, mudanças de etapa, cancelamentos, solicitação de fechamento e
  retomada avançam a versão. Conferência e pagamento usam locks de mesa/sessão;
  uma versão ou total divergente exige nova revisão. A interface destaca a
  alteração junto ao total e bloqueia o pagamento até a confirmação da revisão.
- **Impacto:** uma atualização de versão por alteração do atendimento; o total
  definitivo continua calculado pelo servidor. O pagamento reutiliza esse total
  na gravação, evitando recalculá-lo em duas agregações adicionais. Clientes
  antigos da API de pagamento precisam enviar os dois novos campos obrigatórios.
  A operação continua simulada, identificada assim na interface e na auditoria;
  não foi integrada uma instituição de pagamentos.

## 4. Cancelamento excepcional pelo gerente

- **Risco original:** depois de iniciar preparo, ocorrências reais não tinham
  caminho para retirar um pedido indevido da cobrança sem falsificar etapas.
- **Solução aplicada:** ação separada no detalhe do pedido da gestão, restrita a
  ADMIN. Exige motivo de 10 a 500 caracteres e cancela o pedido inteiro enquanto
  a sessão está ativa e a conta não foi paga. Registra etapa anterior, motivo,
  responsável e horário no histórico e nas atividades administrativas.
  Os preços e itens originais permanecem preservados para consulta.
- **Impacto:** mantém a regra normal de cancelamento antes do preparo. Exceções
  avançam a versão da conta e retiram o pedido cancelado do total. Pagamentos
  concluídos não podem ser alterados por essa ação; devolução financeira depende
  de fluxo próprio, fora desta etapa.

## Publicação e validação

- Migration `0007_historicostatuspedido_motivo_and_more`: versão da conta e
  justificativa no histórico. Migration `0008_comandas_privadas`: acesso individual,
  convites e remoção da restrição de uma conta por mesa.
- O script de inicialização do Render já executa `migrate --noinput`; o build
  coleta os arquivos estáticos. Publicar backend e interface da mesma revisão.
- Suíte completa no PostgreSQL: 166 testes e 158 subtestes aprovados, incluindo
  concorrência. Após ajustes finais de interface/limite, regressões específicas
  também aprovadas. Schema OpenAPI validado sem avisos, JavaScript verificado e
  migrations sem alterações pendentes.
- Navegador local: cliente anônimo escolheu, revisou e enviou o primeiro pedido
  em uma mesa sem sessão, sem login, código ou ação da equipe. Também foram
  conferidos bloqueio no fechamento e invalidação da conferência após retomada. Banco isolado de
  demonstração; nenhuma operação executada na produção.
