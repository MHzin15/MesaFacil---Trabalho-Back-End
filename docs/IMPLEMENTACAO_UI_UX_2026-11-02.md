# Implementação de UI/UX — MesaFácil

Data: 02/11/2026. Base preservada: `873e9f8`, incluindo todas as alterações locais anteriores. Implementação isolada em `codex/ui-ux-20261102`.

Esta entrega aplica a [auditoria aprovada](AUDITORIA_UI_UX_2026-11-02.md) ao aplicativo Django. O protótipo continua separado da aplicação. O Render ativo permanece Free, sem novas dependências, disco pago, gateway ou serviços contratados.

## Patches por problema

| ID | Risco ou atrito original | Solução aplicada | Impacto na arquitetura/performance |
|---|---|---|---|
| UX-01 | Uma comanda parecia representar toda a mesa | Conferência, total e confirmação identificam a comanda; agregado da mesa continua explicitamente agregado | Apresentação; preserva isolamento e permissões |
| UX-02 | Bebidas anunciavam alternativas sem permitir escolher | Grupos configuráveis no editor, obrigatoriedade, uma escolha por grupo e validação no servidor. Água, suco, chopp e refrigerante de exemplo recebem suas opções | Dois campos JSON limitados: configuração no produto e cópia histórica no item; sem joins adicionais no cardápio |
| UX-03 | Observações da cozinha pequenas e identificações comprimidas | Mesa em destaque, identidade em linha própria e observações/adicionais de 16 px; quantidade e produto maiores | CSS e componentes compartilhados, sem consultas extras |
| UX-04 | Horário não mostrava espera | Tempo desde o envio; ordem antiga primeiro preservada. Destaque opcional por minutos, configurado neste aparelho, com 0 para desativar | Cálculo local a cada 30 s, sem gravações, SLA inventado ou serviço agendado |
| UX-05 | Etapas posteriores exigiam atravessar colunas inteiras no celular | Filtro direto Recebidos/Em preparo/Prontos/Todas com contadores; celular inicia em Recebidos, desktop mantém três colunas | Filtra os dados já carregados; sem novas requisições |
| UX-06 | Solicitar conta pausava pedidos sem explicar antes | “Solicitar fechamento” e explicação da pausa antes do botão; retomada continua com a equipe | Regra transacional de fechamento preservada |
| UX-07 | Cabeçalho empurrava o cardápio para baixo | Mesa/comanda compactas, busca prioritária, ajuda recolhível e navegação inferior preservada | CSS responsivo; primeiro produto observado a ~344 px em 390×844 |
| UX-08 | Quem já iniciou recebia ajuda para entrar em outra comanda | Ajuda muda conforme o estado; convite só aparece quando disponível | Estado já fornecido pela API; nenhum login ou intervenção do garçom para começar |
| UX-09 | Não era possível editar escolhas e remoção era imediata | Editar item reabre escolhas, extras, quantidade e observação; desfazer a última remoção local | Só altera rascunho. Desfazer é vinculado à comanda e não altera pedidos enviados |
| UX-10 | Toast encobria quantidade/valor | Feedback em região do conteúdo e dentro dos modais, sem flutuar sobre controles | Mantém anúncios e avisos transacionais; sem overlay de sucesso |
| UX-11 | Revisão duplicava o carrinho | Carrinho é a revisão final, com destino, total e botão Enviar. Mudança entre o clique e a atualização exige novo clique após conferência | Preserva payload pendente imutável, chave de idempotência e validação de total no servidor |
| UX-12 | Mapa alto, contador ambíguo e orientação para abrir atendimento | Mesas compactas, resumo de comandas/fechamentos, expansão para conferir e rótulo Mesas livres | Expansão preservada em atualizações; duas colunas móveis quando cabem |
| UX-13 | Fila de contas escondia valor e pendências | Lista mostra total, pedidos pendentes e tempo da solicitação quando conhecido | Agregações por subconsulta, sem N+1; timestamp novo apenas para solicitações futuras. Legados mostram horário não registrado |
| UX-14 | Pix vinha escolhido e retomada competia com finalizar | Meio inicialmente vazio; confirmação informa comanda, valor e meio. Retomada fica em ajuda secundária com consequência explícita | Mantém versão/total conferidos e recusa pagamento com pedidos pendentes |
| UX-15 | Cadastros grandes vinham antes das pendências | Visão geral começa por atenção/pedidos; indicadores identificam recebimentos simulados e atalhos são menores | Usa consultas existentes |
| UX-16 | Galeria dificultava comparar preço e situação | Lista com miniatura, preço, estado e ações; galeria opcional para prévia | Menor altura por produto; foto lazy-loaded e paginação mantidas |
| UX-17 | Foto mostrava caminho técnico e categoria vazia em inglês | Prévia, Trocar foto/Remover foto própria, limite de 5 MB e categoria em português | Prévia local via object URL, revogada ao sair; validação do servidor mantida |
| UX-18 | Edição apagava busca/categoria/página | Retorno preserva filtros e destaca o registro atualizado | Somente caminho da listagem esperada e filtros conhecidos; bloqueia redirecionamento externo |
| UX-19 | Filtros grandes e formulários pouco orientados | Filtro de acesso recolhível, campos por assunto, resumo da função e mostrar/ocultar senha | Confirmação da senha do gestor, validação e proteção contra auto-bloqueio mantidas |
| UX-20 | Seleção dependia de cor e relógio era anunciado a cada polling | aria-pressed nos filtros, progresso com aria-current preservado, foco/erros associados aos campos e retorno de modal | Relógio sem live region; atualizações só quando os dados mudam |
| UX-21 | Falhas e retomada tinham avisos dispersos | Estado de conexão por fonte, aviso de dados possivelmente antigos e recuperação; consulta da comanda independente do catálogo | Não envia pedidos/pagamentos offline. PWA v6 revalida CSS/JS sem hash, preservando cache de assets imutáveis |
| UX-22 | Títulos e explicações repetidos consumiam espaço | Um título por área; busca da cozinha integrada ao cabeçalho e disponibilidade com ajuda curta | Reduz elementos e mantém URLs e navegação por perfil |

## Proteções adicionais encontradas durante a implementação

- **Escolha renomeada durante a compra:** o catálogo fornece `opcoes_versao`. O servidor compara essa versão com o produto bloqueado antes de aceitar o item. Assim, mudar o nome de uma opção sem mudar o preço também exige nova conferência. Reenvio de pedido já recebido continua retornando o pedido original antes dessa validação.
- **Troca de comanda com personalização aberta:** a janela é fechada ao trocar o contexto privado, evitando editar o carrinho de outra comanda por engano.
- **Compatibilidade com editor anterior:** submissões antigas sem o novo campo de grupos preservam as escolhas existentes.
- **Atualização do PWA:** foi observado CSS anterior durante a conferência. Assets sem hash passam a usar revalidação HTTP; os arquivos com hash continuam usando o cache imutável. API privada e escritas não são armazenadas pelo worker.
- **Navegação inferior da equipe:** espaço inferior reservado, incluindo safe-area, para não esconder as últimas ações.

## Dados e compatibilidade

A migração `0010` adiciona `Produto.grupos_opcoes`, `ItemPedido.opcoes` e `SessaoMesa.conta_solicitada_em`. Os pedidos existentes ficam intactos; observações antigas continuam visíveis. A configuração inicial de opções aplica-se aos quatro nomes exatos de bebidas de exemplo. Produtos personalizados podem ser configurados pelo gestor. Cada grupo aceita uma escolha, opcional ou obrigatória, sem acréscimo; extras com preço continuam sendo adicionais.

Os IDs de grupos/opções são UUIDs e os nomes aceitam até 80 caracteres; até 6 grupos e 12 opções por grupo. O cliente envia IDs e versão; o servidor grava os nomes do catálogo, sem confiar em nomes enviados pelo navegador. Essa cópia evita que a edição posterior de uma escolha altere o histórico.

Para subir esta branch em um banco local de desenvolvimento, aplicar normalmente `python manage.py migrate` antes de servir. A verificação desta entrega utilizou bancos exclusivos de teste/navegador; o banco real e o Render não foram migrados ou publicados. O processo de publicação existente já executa as migrações.

Na inicialização local solicitada posteriormente em 02/11, o PostgreSQL foi religado e o banco de desenvolvimento atualizado de 0006 para 0010, com backup prévio e conferência das contagens existentes. O caminho da cópia está no [guia de retorno](RETORNO_UI_UX_2026-11-02.md). Saúde, início, cardápio e API responderam HTTP 200. Essa atualização foi somente local.

## Validação

- PostgreSQL: **183 testes e 169 subtestes aprovados**, incluindo isolamento entre famílias, reenvio idempotente, concorrência, gestão, pagamento, escolhas obrigatórias, alteração de opção após revisão e matriz de métodos/perfis.
- Após os refinamentos finais dos templates/PWA: **33 testes e 54 subtestes aprovados** nas áreas afetadas.
- Contrato específico do resumo da fila após separar seu serializer: **7 testes e 8 subtestes aprovados**; OpenAPI novamente validado sem warnings.
- JavaScript real em ambiente controlado: troca de comanda durante reenvio, confirmação já recebida, falha apenas do catálogo, resposta atrasada de conta, mudança de preço e mudança de opções antes do envio.
- Worker real em ambiente controlado: revalidação sem hash, cache imutável, fallback público e ausência de interceptação de conta/escrita.
- Django check, migrações sem divergências, OpenAPI validado sem warnings, sintaxe JS e diff sem erros.
- Retorno completo à branch anterior exercitado, com os 229 arquivos conferidos byte a byte e volta à implementação; ajustes de índice do Git no Windows restritos a arquivos idênticos ao commit.
- Navegador local com dados artificiais: escolher água → editar → remover/desfazer → enviar; opção aparece no pedido; cadastrar novo grupo no editor e voltar à busca preservada; cozinha por etapa; mapa com duas colunas; conferência da comanda #5 com meio inicialmente vazio; gestão em 320 px sem overflow horizontal.
- Cozinha por etapa também verificada em 768×1024, sem overflow horizontal; observações de 16 px verificadas no desktop. Linha de produto do gestor observada com 140 px de altura no desktop.

As [capturas da aplicação](uiux/implementacao/README.md) registram a versão local, não o Render. Não houve ensaio em salão real, leitor de tela, teclado virtual físico ou certificação WCAG. A preferência de tempo é local ao aparelho e não equivale a prazo de entrega. A redução para uma única revisão permanece sujeita a avaliação com usuários.

## Retorno à versão anterior

O [guia de retorno](RETORNO_UI_UX_2026-11-02.md) contém o comando, a branch de segurança e a cópia dos bytes originais. Nenhum arquivo do Render Free foi alterado nesta implementação.
