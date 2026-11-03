# Auditoria de UI/UX e proposta de evolução — MesaFácil

**Data:** 02/11/2026. **Escopo:** cliente, garçom, cozinha e gestão.  
**Base:** árvore local da main em 21ddef4, incluindo as correções forenses ainda locais. Não representa necessariamente a interface publicada no Render.  
**Entrega:** diagnóstico + prioridades + critérios de aceite + [proposta navegável](uiux/proposta.html). O layout real não foi redesenhado nesta auditoria.

## Parecer

A identidade visual tem uma base consistente: papel claro, terracota, tipografia de títulos e componentes reconhecíveis. A navegação por perfil, o carrinho com total, as etapas dos pedidos, a busca e o portal próprio de gestão já ajudam.

A prioridade é tornar a operação compreensível à primeira leitura. Há linguagem de “mesa” onde a operação vale só para uma comanda, opções de alimentos anunciadas sem escolha correspondente, informação operacional pequena e áreas de cabeçalho que reduzem a visibilidade das tarefas. Melhorar apenas cores ou arredondamento não resolve esses pontos.

A proposta mantém autoatendimento sem presença do garçom, várias comandas independentes por mesa, convites explícitos para consumir em família e bloqueio de pedidos para o perfil de garçom.

## Decisão de infraestrutura nesta entrega

O proprietário determinou manter o Render **Free até segunda ordem**. O render.yaml ativo voltou a Free para web e PostgreSQL, sem disco pago e sem MEDIA_ROOT de volume. A configuração paga foi preservada somente em deploy/render-paid.yaml.example, sem aplicação automática.

Nenhuma proposta visual requer plano pago, nova plataforma, gateway, WebSocket, serviço de imagens ou assinatura. As limitações de persistência do Free permanecem conhecidas e aceitas por enquanto. [Guia atualizado](RENDER.md).

## Método e limites

- Inspeção visual em navegador da versão local, com banco PostgreSQL exclusivo e dados artificiais: 10 mesas, 15 produtos, múltiplas comandas, pedidos em diferentes etapas e um produto pausado.
- Fluxo de cliente percorrido: busca → refrigerante → sabor/quantidade → carrinho → revisão → envio fictício → pedidos → convite → solicitação de fechamento.
- Funcionários: mapa/entregas/contas do garçom, conferência de comanda entregue, cozinha e disponibilidade, visão geral do gestor, cardápio, editor de produto, equipe, tela de redefinição de senha e relatório.
- Telas observadas em 390×844, 1280×720/800; recortes adicionais de gestão em 320×800 e cozinha em 768×1024. Algumas medições da cozinha estreita foram feitas com o gestor na visão da cozinha, que inclui controles de troca de área.
- Código, templates e CSS examinados para conferir estados, filtros, feedback, preservação de contexto e acessibilidade.
- Referências externas são documentação oficial dos produtos, não acesso às contas ou teste comparativo desses sistemas.
- Não houve pesquisa com clientes/funcionários reais, teste em salão lotado, leitor de tela, ensaio físico em tablet ou certificação WCAG. Metas de tempo abaixo são propostas de aceite, não resultados medidos com pessoas.

**Prova observada** significa verificado em tela/DOM. **Inspeção** significa identificado no código. **Hipótese de projeto** exige teste com usuários antes de tratar a mudança como melhoria comprovada.

## Referências utilizadas e como adaptá-las

| Referência | Padrão relevante | Aplicação proposta no MesaFácil |
|---|---|---|
| [Saipos — cardápio QR](https://saipos.com/cardapio-digital) | Pedido do cliente enviado diretamente à cozinha | Preservar entrada simples e pedido sem depender do garçom |
| [Toast — Mobile Order & Pay](https://support.toasttab.com/en/article/Mobile-Order-and-Pay-Overview) | Jornada contínua de consulta e pedido pelo próprio aparelho | Contexto de comanda visível e continuidade entre pedidos; o pagamento do MesaFácil continua simulado com a equipe |
| [iFood — módulo de cardápio](https://blog-parceiros.ifood.com.br/cardapio-app-do-parceiro/) | Categorias, produto e grupos de complementos com obrigatoriedade/limites | Opções por produto administráveis e distinção clara entre escolhas obrigatórias e extras opcionais |
| [Square — floor plan](https://squareup.com/help/us/en/article/6427-building-your-floor-plan) | Organização visual de mesas e contas durante o serviço | Resumo compacto e leitura por situação; um editor completo de planta não é necessário agora |
| [Toast — configuração de cozinha](https://support.toasttab.com/en/article/Basic-Kitchen-Configuration?lang=en_US) | Tickets, identificação e alertas relacionados ao tempo | Mesa/comanda em destaque, ordem por antiguidade e tempo decorrido visível |
| [Nielsen Norman Group — heurísticas](https://www.nngroup.com/articles/ten-usability-heuristics/) | Linguagem da pessoa, visibilidade de estado e prevenção de erro | Rótulos consistentes, feedback persistente quando necessário e identidade explícita nas ações |
| [WCAG — alvos](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) e [reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html) | Alvos e adaptação a largura reduzida | Revisar teclado, foco e sobreposições; preferir alvos de 44–48 px para o salão |

A WCAG 2.2 AA define alvo mínimo de 24×24 CSS px com exceções. A meta de 44–48 px deste projeto é uma recomendação de conforto operacional; não classifique um botão de 36 px como falha AA apenas pelo tamanho. Tabelas podem ter exceção de reflow: rolagem interna não equivale automaticamente a falha.

## Problemas e melhorias, por prioridade

**P1:** risco relevante de escolha errada ou tarefa operacional difícil. **P2:** atrito frequente ou hierarquia ruim. **P3:** refinamento. Nenhum P0 de UI foi demonstrado.

| ID | Prioridade | Problema identificado | Melhoria projetada | Evidência |
|---|---|---|---|---|
| UX-01 | P1 | Modal de uma comanda usa “Total da mesa”; links do cliente também alternam mesa/comanda | Sempre mostrar “Comanda #N · Mesa NN” e “Total desta comanda”; agregado da mesa apenas em visão explicitamente da equipe | Observado: modal da comanda #5 e link “Ver conta da mesa” |
| UX-02 | P1 | Água oferece “com ou sem gás” no texto, mas o modal não permite escolher. Sucos e chopp também anunciam alternativas; somente refrigerante tem seletor implementado | Grupos de opções por produto, com “Escolha 1 · obrigatório”, salvos de forma estruturada e validados no servidor | Água confirmada em tela; demais por catálogo/código |
| UX-03 | P1 | Observações e adicionais importantes da cozinha estão em 12 px; mesa/comanda quebram linhas em cartões estreitos | Fonte operacional de 16–18 px, quantidade/mesa grandes e observações destacadas sem depender só de cor | DOM/CSS medidos em 1280 px; tickets de ~273 px de largura |
| UX-04 | P1 | Cozinha mostra horário absoluto, sem idade legível do pedido; não ajuda a reconhecer espera prolongada | “Pedido há 14 min”, ordem antiga primeiro e limiares de atenção configurados pelo restaurante; tempo de etapa só com dado confiável | Horário absoluto observado; ausência de temporizador por inspeção |
| UX-05 | P1 | No celular, todas as colunas da cozinha ficam uma abaixo da outra; etapas posteriores exigem longa rolagem | Abas/filtro de etapa com contadores no topo e lista da etapa escolhida; manter colunas no desktop | Em 390 px com gestor: preparação a ~1373 px e prontos a ~2137 px do viewport no recorte avaliado |
| UX-06 | P1 | “Pedir a conta” pausa novos pedidos imediatamente, mas essa consequência aparece depois da ação | Informar a consequência antes: “Solicitar fechamento” e mensagem curta sobre retomada; confirmação contextual se necessária | Fluxo fictício de fechamento percorrido |
| UX-07 | P2 | Bloco de cabeçalho + mesa + explicação de família empurra os alimentos para baixo | Cabeçalho compacto com Mesa e Comanda, ajuda expansível e busca/categorias antes dos cartões | Primeiro produto começou em ~640 px no viewport 390×844, com página no topo |
| UX-08 | P2 | Ajuda de família continua dizendo para entrar no convite de quem começou mesmo para quem já começou; botão de compartilhar aparece desativado antes do primeiro envio | Texto por estado: antes do primeiro envio, explicação curta; depois, “Convide quem vai consumir com você”; sem bloco vazio de ação indisponível | Observado antes/depois do pedido |
| UX-09 | P2 | Carrinho permite remover e alterar quantidade, mas não editar sabor/adicionais/observação. Remoção é imediata | “Editar item” reabre o formulário preenchido; remoção local permite desfazer; ação nunca altera pedido já enviado | Observado no carrinho e confirmado no JS |
| UX-10 | P2 | Mensagem flutuante de sucesso cobre a região da quantidade/valor quando o usuário abre o carrinho rapidamente | Confirmação próxima da ação ou faixa fora da área dos controles; nenhum aviso cobre CTA, input ou preço | Sobreposição observada depois de adicionar bebida |
| UX-11 | P2 | Carrinho é seguido por outra revisão quase igual; adiciona uma decisão sem acrescentar muita informação | Avaliar confirmação no próprio carrinho com total e destino explícitos. Se preço/contexto mudar, exigir nova revisão. Não remover a proteção transacional | Duplicidade observada; redução de etapa é hipótese a validar |
| UX-12 | P2 | Mesa tem cartão alto e um botão por comanda; contador “Mesas 5” significa livres, não total. Texto ainda orienta “Abra o atendimento” | Grade compacta; “3 comandas / 1 conta solicitada”; contadores com significado e texto alinhado ao primeiro pedido automático | Mapa do garçom observado |
| UX-13 | P2 | Fila de contas tem título e CTA repetidos, sem total, espera ou pendências antes de abrir | Valor, comanda, idade da solicitação e pedidos pendentes na lista; CTA “Conferir comanda #N” | Duas contas fictícias observadas |
| UX-14 | P2 | Pagamento vem com Pix pré-selecionado; ação de retomar recebe destaque próximo de finalizar e há botão “Conta já solicitada” sem ação útil | Exigir escolha explícita do meio; destacar identidade/valor na confirmação; retomada como ação secundária com consequência clara | Modal observado; simulação não foi confirmada |
| UX-15 | P2 | Painel do gestor prioriza indicadores e três grandes atalhos de cadastro antes das pendências | “Precisa de atenção” primeiro; cadastros como atalhos menores ou destaque apenas na primeira configuração | Visão geral observada |
| UX-16 | P2 | Galeria de produtos usa imagens grandes e ações pequenas para tarefa de comparar preços/disponibilidade | Lista compacta no desktop com miniatura, nome, preço, situação e ação de 44 px; cartões correspondentes no celular; galeria opcional para conferir apresentação | Cardápio do gestor observado |
| UX-17 | P2 | Editor de imagem mostra caminho técnico e “Limpar/Modificar”; opção vazia da categoria aparece em inglês | Prévia visual, “Trocar foto/Remover foto”, limite de arquivo, linguagem pt-BR e estado sem imagem explícito | Editor de produto observado |
| UX-18 | P2 | Salvar preço/disponibilidade/cadastro retorna à listagem sem preservar busca, categoria e página | Guardar filtros/posição e voltar ao item editado, com confirmação no contexto | Inspeção de redirects nas views de gestão |
| UX-19 | P2 | Filtros da equipe ocupam muito espaço no celular; primeira pessoa aparece perto do fim da tela. Formulários podem orientar melhor recuperação e permissões | Busca curta visível; filtros adicionais recolhíveis; campos por grupo, resumo da função e mostrar/ocultar senha sem enfraquecer confirmação do gestor | Lista e reset observados; demais formulários por inspeção |
| UX-20 | P2 | Categoria selecionada depende de classe/cor; progresso não anuncia claramente a etapa atual. Atualização de relógio tem role=status a cada polling | aria-pressed nos filtros, aria-current=step no progresso e anúncios apenas para alterações relevantes; validação guiada e foco restaurado | DOM/JS examinados; leitor de tela não ensaiado |
| UX-21 | P2 | Estados de conexão, atualização antiga e retomada dependem de mensagens dispersas. Free pode acrescentar espera inicial | Especificar estado “atualizando/sem conexão/dados antigos/recuperado”, sem ocultar pedido pendente ou prometer entrega offline | Fonte inspecionada; falha de rede não foi injetada nesta avaliação visual |
| UX-22 | P3 | Títulos e explicações repetidos, como disponibilidade, consomem área sem acrescentar decisão | Um título por tela, ajuda contextual só onde muda a ação e resumo compacto | Cozinha/disponibilidade e gestão observadas |

## O que deve ser preservado

- Paleta de papel/terracota e contraste corrigido na etapa anterior.
- Navegação inferior móvel do cliente e divisão dos painéis por perfil.
- Produto pausado identificado e sem botão ativo de compra.
- Totais explícitos no carrinho, revisão de preço alterado e idempotência.
- Convite familiar com confirmação de entrada; QR público não abre conta alheia.
- Identificação de pagamento simulado e conferência de versão/total.
- Proteção contra auto-bloqueio do gestor e confirmação da sua senha no reset.
- Equipe já se adapta a cartões no celular, sem forçar a tabela inteira para fora do viewport.
- Ausência de overflow horizontal da página nos recortes medidos; a barra de categorias tem rolagem própria, intencional.

## Projeto de interface por perfil

### Cliente — decidir rápido e ter confiança no envio

Ordem proposta: marca pequena + Mesa → contexto da própria comanda → busca → categorias → produtos. A ajuda para família aparece compacta e pode ser expandida. A navegação continua Cardápio, Carrinho, Pedidos e Conta.

Antes do primeiro pedido, o rascunho não precisa exibir número inexistente. Depois do envio, mostrar número da comanda. Não introduzir login obrigatório, código digitado ou autorização do funcionário para começar.

Personalização: título/foto curtos, escolhas obrigatórias com legenda e contagem, adicionais opcionais com preço, observação opcional e quantidade com alvos grandes. O total acompanha a escolha e o botão informa a ação. Para bebidas diferentes, cadastrar linhas separadas, cada uma com sua opção.

Carrinho: itens editáveis, desfazer remoção local e um total final. Destino “Comanda #N · Mesa NN” perto de enviar. Pedido enviado recebe confirmação persistente com número; nunca interpretar timeout como falha definitiva ou iniciar outro envio automaticamente.

Conta: separar rascunho, pedidos enviados, pedidos cancelados e valor devido. Pedir fechamento informa antes a pausa de novos pedidos. O cliente anterior continua sem ver novas famílias após encerramento.

### Garçom — localizar, entregar e fechar a conta correta

Entrada pelo resumo do trabalho, sem obrigar o garçom a abrir mesas. Grade de duas colunas no celular quando couberem alvos adequados; número grande e estados escritos. A mesa pode ter várias comandas, então “uma conta solicitada” não significa que todo mundo está fechando.

A fila de entregas distingue retirar e confirmar entrega. A fila de contas deve mostrar valor e pendências antes do modal. Abrir uma mesa leva às suas comandas, sem obrigar a navegar por todo o salão novamente.

Conferência: título, total e CTA usam a mesma comanda. Meio sem valor padrão e confirmação “Comanda #5 · R$ 53,70 · Pix”. A retomada não compete visualmente com a finalização e informa que libera novos pedidos. Pagamento real continua fora do escopo.

### Cozinha — ler de longe e agir durante o pico

Cabeçalho de operação curto e modo de maior área útil, sem grande painel de perfil. Desktop mantém colunas; celular oferece acesso direto às etapas. O primeiro pedido fica alto no viewport, sem atravessar texto institucional.

Ticket: Mesa NN em primeiro plano, Comanda #N/Pedido #N legíveis, idade do pedido, quantidades e observações. Não truncar restrições/observações. Cor reforça texto; não é o único sinal de prioridade.

Uma ação principal por etapa: iniciar preparo ou marcar pronto. Cancelar é secundário e mantém confirmação com identificação do pedido. Não acrescentar um “desfazer” que o backend não possa realizar com segurança.

Som só como opção explicitamente ativada por quem usa, acompanhado de sinal visual e acessível. Não prometer notificação em segundo plano; o polling atual não é push. Não inventar previsão de entrega sem dados confiáveis.

### Gestor — controlar a rotina e manter o cadastro

Visão geral começa pelas pendências acionáveis. Indicadores mostram período, unidade e natureza simulada. Atalhos de criar equipe/mesa/produto continuam disponíveis com menor área quando a operação já está cadastrada.

Cardápio: lista para editar e comparar; galeria como prévia. Editor agrupa “Informações”, “Preço”, “Foto” e “Venda”, com prévia de como aparece ao cliente. Se grupos obrigatórios forem adicionados ao modelo, serão configurados neste mesmo contexto.

Equipe: nome, função, estado e ação reconhecíveis. Recuperar senha identifica funcionário e gestor com clareza e preserva a validação de segurança. Formulários oferecem resumo de erros com link para o campo e aviso ao sair com mudanças não salvas.

## Critérios de design e aceite

| Tema | Critério proposto para implementação |
|---|---|
| Identidade | Toda ação de conta mostra mesa e comanda; “total da mesa” só em agregado explícito |
| Entrada móvel | Em 390×844 no topo, buscar/categorias e ao menos um produto completo antes da navegação inferior; meta de primeiro produto até ~350 px |
| Toque | Ações frequentes com 44–48 CSS px, espaço entre ações perigosas e normais |
| Texto | Base do cliente ~16 px; cozinha 16–18 px para dados importantes; títulos de mesa 22–26 px conforme viewport |
| Cabeçalhos | Um nível de navegação que acompanha a rolagem com fundo opaco e separação; conteúdo com espaço reservado, sem menus flutuando sobre produtos |
| CTA fixo | Total e ação visíveis, com padding inferior suficiente; teclado virtual, mensagens e safe-area não cobrem campos nem ações |
| Cores | Terracota para principal, verde para conclusão, âmbar para atenção; texto/ícone distinguem estados |
| Acessibilidade | Teclado, foco de modal/retorno, estados semânticos, mensagens ligadas aos campos e contraste mínimo adequado ao texto |
| Kitchen | Etapa acessível por seleção direta em celular; observação completa visível e sem truncar |
| Gestão | Voltar da edição preserva filtros/página e mostra o item atualizado |
| Resiliência | Estado de erro informa próxima ação; tentativas pendentes são recuperadas sem duplicar e sem esconder conta existente |
| Infraestrutura | Tudo funciona na configuração Free atual, sem novas contratações |

São metas de projeto. Não foram todas implementadas no aplicativo nem medidas com usuários reais.

## Ordem de execução recomendada

1. **Correções de clareza e escolha (P1):** escopo mesa/comanda, água/suco/chopp, fechamento e identidade da confirmação. Grupos de opções exigem modelagem/validação de servidor; não resolver só escrevendo o sabor numa observação.
2. **Operação da cozinha:** tipografia, tempo decorrido, área útil e acesso móvel às etapas.
3. **Cliente:** primeiro viewport, ajuda de família por estado, edição de carrinho e feedback sem sobreposição. Comparar revisão única com a atual usando tarefas reais.
4. **Salão:** mesas compactas, contadores claros, fila de contas com total/pendências e meio de pagamento explícito.
5. **Gestão e acessibilidade:** prioridades do dashboard, lista de catálogo, imagem, filtros preservados, formulários e semântica de estado.
6. **Validação com pessoas:** ajuste fino, teclado, leitor de tela e ensaio no restaurante.

Não começar por animações, editor de planta completo, temas extras ou funções de ERP sem relação com as tarefas avaliadas.

## Roteiro de validação com usuários

Usar dados fictícios e pelo menos um cliente novo, uma pessoa de salão, uma de cozinha e o responsável pelo cadastro. Para comparação mais confiável, repetir com mais participantes e alternar a ordem das versões; não tirar percentual de ganho de uma única tentativa.

- Cliente: pedir duas águas com opções diferentes; alterar uma escolha antes de enviar; localizar o pedido; entender que está em conta separada; entrar na conta da família por convite.
- Garçom: localizar mesa com três comandas, entregar pedido e fechar somente uma delas; identificar conta pendente sem abrir todas.
- Cozinha: achar o pedido mais antigo, ler observação, iniciar e concluir preparo em 390, 768 e 1280 px.
- Gestor: pausar produto, mudar preço, voltar à busca anterior, cadastrar funcionário e encontrar recuperação de senha.
- Recuperação: simular conexão instável e preço alterado sem criar duplicidade ou permitir cobrança errada.
- Registrar conclusão sem ajuda, erros de comanda/opção, tentativas repetidas e tempo até a primeira ação útil. A meta é zero erro de identidade/total, não um número de cliques isolado.
- Verificar 320 px, zoom de 200%/400% conforme contexto, teclado e leitor de tela. Navegador com viewport reduzido não substitui aparelho físico.

## Material entregue

- [Proposta navegável das quatro jornadas](uiux/proposta.html), com dados fictícios e interações locais. Não é uma nova versão do aplicativo e não tem acesso à API.
- Exemplos visuais: [cliente proposto](uiux/proposta-cliente.jpg) e [cozinha proposta](uiux/proposta-cozinha.jpg).
- [Cliente atual no celular](uiux/evidencias/cliente-mobile-atual.jpg).
- [Água sem seletor de gás](uiux/evidencias/agua-sem-opcoes.jpg).
- [Cozinha atual no desktop](uiux/evidencias/cozinha-desktop.jpg) e [tablet](uiux/evidencias/cozinha-tablet.jpg).
- [Visão geral do gestor](uiux/evidencias/gestao-desktop.jpg), [catálogo atual](uiux/evidencias/cardapio-gestao-desktop.jpg) e [equipe móvel](uiux/evidencias/equipe-mobile.jpg).

Não houve mudança dos layouts reais, push, deploy ou alteração de dados de produção. O banco de revisão é isolado. As modificações desta etapa no aplicativo se limitam à manutenção da configuração Render Free e documentação associada.

## Conferência dos entregáveis

A configuração YAML foi lida e conferida: web/banco Free, sem disco e sem variável
de mídia paga; exemplo pago separado. O check Django passou. Na proposta foram
percorridos escolha obrigatória da água, quantidade/total, carrinho editável,
seleção explícita de meio para uma comanda, filtro de etapa da cozinha e edição
de preço mantendo a busca. Imagens locais carregaram. Essas verificações do
protótipo não são testes de aceite da futura implementação no aplicativo.
