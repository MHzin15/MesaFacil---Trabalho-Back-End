# Um responsável por mesa — regra vigente

## Experiência aprovada

1- Uma pessoa lê o QR da mesa livre. Esse aparelho assume o atendimento e faz os pedidos de todo o grupo, sem login e sem precisar do garçom.

2- Outro aparelho recebe **“Esta mesa já está em atendimento”**. Ele não vê pedidos, conta ou carrinho do responsável. Foram retirados convites, compartilhamento, seletor de comandas e abertura de contas separadas pelo cliente.

3- Sem pedido enviado, a reserva expira após **5 minutos sem atividade**. Interações reais renovam esse prazo, no máximo uma vez a cada 30 segundos. Consultas automáticas não renovam. O carrinho ainda não enviado não mantém a mesa ocupada indefinidamente.

4- Depois do primeiro pedido, o atendimento não expira por inatividade. O pagamento confirmado encerra a sessão e libera a mesa. **O pagamento continua simulado neste MVP**, sem cobrança bancária automática. A próxima família lê o mesmo QR e inicia um atendimento independente.

5- O aparelho anterior não recebe o próximo atendimento pelo polling. Sem acesso válido, a tela deixa de exibir pedidos e conta. Um novo início explícito só é permitido se a mesa estiver livre.

6- Na perda de acesso, o novo aparelho solicita a troca e mostra um código à equipe. No mapa de mesas, garçom ou administrador confere o código e autoriza. Ele vale 5 minutos; não é senha nem convite para entrar sozinho. A troca bloqueia o aparelho anterior e mantém sessão, pedidos e valores.

## Patches: risco, solução e impacto

| Risco original | Solução aplicada | Impacto na arquitetura ou performance |
| --- | --- | --- |
| Compartilhamento e contas separadas contrariavam a experiência pedida. | Uma capacidade privada por mesa e tela de mesa em uso; convites/seleção antigos respondem HTTP 410. | Histórico financeiro preservado; interface do cliente reduzida ao próprio atendimento. |
| Leituras simultâneas poderiam eleger dois responsáveis. | Reserva e primeiro pedido serializados com bloqueio transacional da mesa. | Disputa restrita à mesma mesa; reserva vazia não cria conta financeira. |
| Leitura sem consumo poderia prender a mesa. | Expiração por horário, renovada apenas com atividade real. | Sem cron, fila, Redis ou serviço adicional; compatível com Render Free. |
| Transferência poderia manter o antigo celular autorizado. | Rotação da capacidade; autorização da equipe e revalidação dentro das transações de pedido e solicitação de conta. Leituras privadas serializam com a transferência. | Preserva IDs e valores; bloqueios curtos por mesa evitam corridas. Dados já vistos no aparelho não podem ser apagados remotamente. |
| Solicitação antiga poderia tomar a mesa da próxima família. | Solicitação vinculada ao responsável vigente na criação; aprovação recusa atendimento diferente ou prazo vencido. | Validação adicional; outras solicitações expiram após aprovação. |
| Solicitações no painel poderiam gerar consultas por mesa. | Prefetch de solicitações válidas. | Mapa passa de duas para três consultas constantes, sem crescimento por quantidade de mesas. |
| Confirmação de transferência pouco clara. | Janela com mesa, código, efeito da troca e confirmação explícita. | Sem caixa nativa do navegador; identidade da solicitação revisada preservada até a ação. |

## Migração e atendimentos já abertos

A migração **0011** adiciona reserva e transferência. Capacidades das sessões antigas abertas são revogadas, pois antes podiam ser compartilhadas: não é possível eleger com segurança qual celular deve ser o responsável.

**Atendimentos abertos na atualização precisam de uma transferência autorizada pela equipe para o celular correto, uma única vez.** Mesas livres continuam iniciando sem garçom. Pedidos, itens, preços, pagamentos e sessões não são apagados ou somados.

Se uma mesa antiga tiver várias contas abertas, a equipe pode consultá-las e fechá-las separadamente. A transferência é recusada até restar um atendimento. Não houve fusão automática de contas financeiras.

Backend, migração e estáticos devem ser publicados juntos. Worker atualizado para v7. Configurações do Render Free, plano, dependências e processo de publicação mantidos.

## Validação e retorno

- PostgreSQL: **183 testes e 169 subtestes aprovados**. Inclui disputa real de duas leituras do QR, expiração, isolamento, transferência, permissões, reenvio e pagamento.
- Após os últimos ajustes: **23 testes e 6 subtestes aprovados**, incluindo tentativa de solicitar conta com capacidade revogada diretamente no serviço.
- Verificadores JavaScript de reenvio, catálogo indisponível, mudança de opções e resposta atrasada de conta aprovados. Sintaxe JS, Django check, migrações e OpenAPI sem divergências ou warnings.
- Navegador com dados artificiais: envio, bloqueio do segundo aparelho, solicitação, confirmação pelo garçom e bloqueio do aparelho revogado. Tela bloqueada em 390 px sem rolagem horizontal. [Capturas locais](uiux/responsavel-unico/).
- Banco local atualizado para 0011 após dump nativo validado. Hashes de **66 registros em 13 tabelas anteriores** preservados, excluindo somente capacidades de acesso deliberadamente rotacionadas. Cópia mais recente: `.local/antes-aplicar-responsavel-unico-20261102-235648/` (dump, mídia e manifesto). Cópia anterior: `.local/antes-responsavel-unico-20261102-234259/`.

Checkpoint `codex/checkpoint-uiux-20261102` em `873e9f8` preservado. Revisão publicada anterior: `50a004e`. Retorno de arquivos não desfaz migração, pedidos ou rotação de acessos. Para recuperar também dados, restaure em outro banco vazio conforme [RECUPERACAO.md](RECUPERACAO.md), preservando o atual. Não reverta migrações financeiras para voltar a interface.

Evidências locais; não representam teste em salão real, dispositivo físico ou confirmação do deploy no Render.
