# Correções da auditoria forense — 02/11/2026

Base: [auditoria integral](AUDITORIA_FORENSE_INTEGRAL_2026-11-02.md), commit
`21ddef4`. As correções preservam pedido sem presença do garçom, várias comandas
privadas na mesma mesa e encerramento individual após pagamento simulado.

## 1 — MF-01: identidade imutável do envio

- **Risco original:** outra aba podia trocar a comanda selecionada e fazer um
  retry criar outro pedido em outra comanda.
- **Solução:** primeiro envio carrega `atendimento_id`, autorizado entre os
  acessos privados do navegador. Rascunhos anteriores permanecem autorizados
  para sua própria tentativa; a API resolve o destino explícito e a chave
  original. O campo não muda o hash do conteúdo dos envios existentes. Clientes
  antigos com `sessao_id` fixo continuam seguros; primeiro pedido sem identidade
  recebe conflito e exige atualização. Tentativas salvas no navegador recebem
  a identidade do rascunho da sua própria chave de armazenamento.
- **Impacto:** validação adicional no acesso; não cria contas vazias nem exige
  abertura por funcionário. Leituras, convite e solicitação de conta também
  usam a identidade da aba para não misturar respostas.
- **Validação:** retry após novo rascunho retorna o mesmo pedido e mantém uma
  única comanda; outro navegador não usa a identidade. JS real validado em
  corrida e controle estável.

## 2 — MF-02: locks compatíveis com a chave estrangeira

- **Risco original:** ciclo de locks entre produto e adicional abortava uma
  edição/pedido concorrente por deadlock PostgreSQL.
- **Solução:** produtos do pedido usam `FOR NO KEY UPDATE`, que mantém exclusão
  de mudanças de preço/disponibilidade e permite `KEY SHARE` da FK. O vínculo
  do adicional continua revalidado após seu lock.
- **Impacto:** específica ao PostgreSQL, banco obrigatório da aplicação; mantém
  atomicidade. Se o adicional mudou de produto, o pedido é recusado inteiro.
- **Validação:** interleaving real antes defeituoso terminou sem deadlock; edição
  preservada e pedido com adicional incompatível recusado sem itens parciais.

## 3 — MF-03: guardas administrativas em todos os acessos

- **Risco original:** as URLs técnicas de usuários/perfis contornavam a senha
  de confirmação e a proteção contra auto-suspensão/rebaixamento do gestor.
- **Solução:** alterações técnicas de usuários e perfis são exclusivas do
  superusuário responsável; gestores usam o portal com suas guardas existentes.
  A restrição é aplicada à permissão da URL, inclusive reset de senha.
- **Impacto:** o responsável técnico conserva suporte administrativo. O fluxo
  do chefe do restaurante continua em Equipe e acessos.
- **Validação:** três operações alternativas negadas, sem alteração de senha,
  atividade ou papel; cadastro pelo portal permanece permitido e auditado.

## 4 — MF-04: modal e operação da mesma comanda

- **Risco original:** resposta atrasada A substituía o modal B enquanto a ação
  usava o ID B.
- **Solução:** seleção tem versão; respostas antigas são descartadas, dados e
  conferência são limpos ao trocar/fechar modal e ações capturam o ID exibido.
  Pagamento confere também identidade e total do snapshot revisado.
- **Impacto:** tratamento local da concorrência de interface, sem alterar API
  financeira nem as comandas da mesa.
- **Validação:** JS real recebeu A depois de B e manteve título e fechamento B.

## 5 — MF-05: formulário antigo não restaura preço antigo

- **Risco original:** editar descrição em formulário obsoleto podia desfazer um
  ajuste de preço feito depois de sua abertura.
- **Solução:** o formulário completo guarda preço original e o compara ao
  registro bloqueado no POST, tanto no portal quanto no admin técnico.
- **Impacto:** em conflito, a pessoa deve reabrir e revisar; pedidos anteriores
  continuam com seus snapshots. Nenhuma mudança de preço fica silenciosa.
- **Validação:** preço 10→12 no ajuste rápido permaneceu 12 após POST antigo;
  fluxo sem conflito e log de alteração de preço continuam aprovados.

## 6 — MF-06: mesa com histórico recebe conflito explicado

- **Risco original:** `ProtectedError` retornava HTTP 500 ao excluir mesa.
- **Solução:** resposta HTTP 409 orienta desativar após encerrar comandas.
- **Impacto:** mantém `PROTECT`, registros e histórico; mesa sem uso pode ser
  excluída normalmente.
- **Validação:** mesa histórica preservada com 409; mesa vazia excluída com 204.

## 7 — MF-07: persistência, backup e recuperação

> Decisão posterior do proprietário: manter o Render Free até segunda ordem.
> A configuração ativa foi restaurada para Free e a proposta paga está somente
> em `deploy/render-paid.yaml.example`. O risco de persistência do plano gratuito
> permanece aceito por enquanto. Nenhuma compra é exigida para rodar os patches.

- **Risco original:** Blueprint Free com mídia efêmera, banco que expira e falta
  de rotina ensaiada de recuperação de banco e fotos.
- **Solução no repositório:** exemplo futuro pago com banco durável e disco; a raiz permanece Free;
  `MEDIA_ROOT` configurável; Compose mantém seu volume. Foi adicionado o comando
  `snapshot_restaurante` com snapshot PostgreSQL consistente, mídia e hashes.
  A restauração só aceita banco/pasta vazios, valida arquivos e compara todos os
  registros de domínio e fotos. Procedimento em [RECUPERACAO.md](RECUPERACAO.md).
- **Impacto:** os planos de produção têm custo. Disco atende uma instância web;
  storage de objetos pode substituí-lo quando houver várias instâncias. Nenhum
  serviço foi contratado ou alterado nesta tarefa.
- **Validação:** dump/restore real em dois bancos descartáveis, com duas comandas,
  pagamento, foto e comparação completa; recusa de sobrescrita confirmada.
- **Ativação externa pendente:** revisar/aplicar planos na conta Render, copiar
  fotos existentes, ativar agenda de cópias externas e medir o RPO/RTO real.
  A configuração não recupera arquivos já perdidos no serviço Free.

## 8 — MF-08: mesmo limite de foto em todos os canais

- **Risco original:** API aceitava foto válida maior que os 5 MB do portal.
- **Solução:** validador compartilhado no campo de imagem do modelo, herdado
  por formulário, serializer e admin. Editar sem substituir foto antiga grande
  permanece permitido; arquivos legados não são apagados.
- **Impacto:** limite de upload coerente, sem dependências ou processamento extra.
- **Validação:** imagem PNG válida de aproximadamente 7 MB recusada na API e
  portal sem criar produto ou gravar a foto. Migration altera o validador.

## 9 — MF-09: redação de capacidades nos logs

- **Risco original:** URLs de convite e contexto privado apareciam em access logs.
- **Solução:** filtro Django e logger Gunicorn redigem segmentos privados,
  request-line, query e mensagens de exceção. Gunicorn não registra Referer nem
  User-Agent. Render, Docker e Compose carregam a configuração de logging.
- **Impacto:** mantém rota/status/latência para diagnóstico, sem token nos logs
  controlados pela aplicação. Não modifica registros históricos.
- **Validação:** tokens sintéticos ausentes de mensagens formatadas e caminhos.
- **Limite externo:** acesso, retenção e redação dos logs de borda/proxy precisam
  ser configurados no provedor; o filtro da aplicação não administra esses logs.

## 10 — MF-10: prontidão observa o banco

- **Risco original:** health check em `/` respondia saudável mesmo sem banco.
- **Solução:** `/health/live/` mede processo; `/health/ready/` executa `SELECT 1`
  e retorna 503 se o banco falhar. Conexão tem timeout de 3 s, consulta 2 s e
  espera por lock 1 s. Blueprint usa readiness.
- **Impacto:** uma consulta pequena por sonda; respostas sem configuração ou
  texto de exceção, sempre sem cache. Liveness segue independente do banco.
- **Validação:** banco normal=200; falha injetada=503; liveness=200 nos dois.

## 11 — MF-11: contraste legível

- **Risco original:** texto secundário tinha contraste abaixo de 4,5:1.
- **Solução:** tom secundário ajustado de `#74786d` para `#62675d`.
- **Impacto:** mantém papel/terracota e hierarquia visual do site, sem custo de
  runtime. Contraste calculado passou para 5,32:1 no papel e 5,75:1 na superfície.
- **Limite:** não equivale a certificação de acessibilidade de todas as telas.

## 12 — MF-12: conta atualiza com falha de catálogo

- **Risco original:** catálogo com erro interrompia pedidos e conta no polling.
- **Solução:** leituras independentes, atualização compartilhada entre chamadas
  simultâneas e timeout de rede. Cardápio inválido bloqueia novo envio, enquanto
  recuperação idempotente de tentativa e consulta de conta permanecem possíveis.
- **Impacto:** não cria fila financeira offline; preços seguem conferidos pelo
  servidor. Troca de comanda limpa dados antigos enquanto carrega o novo destino.
- **Validação:** JS real recebeu falha de catálogo e manteve conta/andamento e
  identidade do retry; controle normal também aprovado.

## 13 — MF-13: adicionais paginados em ordem estável

- **Risco original:** queryset sem ordem padrão produzia aviso e páginas instáveis.
- **Solução:** lista da API ordenada por chave primária.
- **Impacto:** usa índice existente; filtros continuam disponíveis. Nenhuma nova
  tabela ou índice foi necessário.

## 14 — MF-14: downgrade destrutivo bloqueado

- **Risco original:** reverter 0008 poderia eliminar identidades privadas e
  tentar impor uma conta ativa por mesa a dados com várias contas.
- **Solução:** migration 0009 bloqueia downgrade antes de reverter operações;
  runbook orienta correção para a frente ou restauração isolada de backup.
- **Impacto:** voltar o banco exige procedimento explícito de recuperação; a
  regra multi-comanda permanece. Migrations já aplicadas não foram reescritas.
- **Validação:** reversão de 0009 recusada com dados preservados no ensaio PG.

## 15 — MF-15: documentação atual e fotografias históricas

- **Risco original:** aceite/plano de outubro pareciam descrever sessão única
  como regra vigente.
- **Solução:** documentos históricos marcados; README aponta comandas privadas
  e novo contrato; guia Render e recuperação descrevem a configuração atual.
- **Impacto:** preserva evidências antigas com seu contexto, sem alterar regras.

## Verificação e estado de entrega

Regressões executadas em banco PostgreSQL local descartável; harnesses Node
executam os arquivos reais do cliente e do garçom com respostas controladas.
Validação estrita de OpenAPI, checks Django, consistência de migrations e
dependências também executados. Ensaio de restore foi feito em bancos novos.
Os resultados finais estão no registro de validação desta entrega.

| Verificação final | Resultado |
|---|---|
| Suíte completa PostgreSQL + matriz de métodos | **176 testes e 161 subtestes aprovados**, 89,38 s |
| Matriz de autorização/contrato | 399 requisições; **zero 5xx**; exclusão histórica retorna 409 |
| JS real do garçom | Resposta atrasada descartada; modal e operação permanecem em B |
| JS real do cliente | Controle estável sem reenvio; corrida mantém destino A; falha de catálogo não bloqueia conta |
| Backup e restauração | Registros/valores/fotos iguais; sobrescrita e downgrade recusados |
| Django/migrations | Sem problemas; nenhum model sem migration |
| OpenAPI e dependências | Schema estrito aprovado; pip check sem incompatibilidades |
| Contraste secundário | 5,32:1 no papel e 5,75:1 na superfície |

Não houve validação de Docker/Gunicorn em runtime Linux nem ensaio em aparelhos
físicos nesta entrega. A prova JS usa DOM/API controlados e os arquivos reais da
aplicação. O plano de capacidade e os avisos de scanners sem vulnerabilidade
demonstrada permanecem como avaliação, sem mudanças artificiais de arquitetura.

Alterações estão locais para revisão. Não houve migração de produção, push, deploy, contratação
de planos ou modificação de dados de produção. MF-07 e a política operacional de
logs dependem da ativação no provedor e não são declarados resolvidos em produção.
