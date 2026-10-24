# MesaFácil — conferência final do plano e do enunciado

Referência: [avaliação e plano](AVALIACAO_E_PLANO_2026-10-23.md), requisitos
fornecidos pelo usuário e [registro das etapas](EXECUCAO.md).

## Resultado e limites

O MVP está implementado e o fluxo completo foi validado em PostgreSQL e Chrome.
Esta é uma conclusão técnica do código: o aceite presencial do semestre ainda
depende da demonstração em dois aparelhos físicos e da apresentação pela dupla.
Não foi executado Docker/Gunicorn Linux nesta máquina, onde Docker não está disponível.
O banco usado pela aplicação e pela validação final é PostgreSQL, não SQLite.

- PostgreSQL 18.6: **79 testes aprovados**, incluindo cinco cenários de concorrência
  com conexões reais. `check`, migrations, `collectstatic`, OpenAPI estrito e
  `pip check` também passaram.
- Chrome 155, Playwright 1.62.1: cliente 390×844, cozinha 1280×800 e garçom 1024×768,
  com logins e sessões independentes. Fluxo completo sem chamada manual de API
  para operar o atendimento; nenhum erro JavaScript ou rolagem horizontal.
- Pedido de referência com quantidade 2: `(32,90 + 5,00 + 4,00) × 2 = 83,80`.
  Cozinha recebeu, preparou e marcou pronto; garçom retirou, entregou, conferiu e
  aprovou cartão simulado; cliente viu encerramento e mesa voltou a ficar livre.
- Regressões de navegador: disponibilidade, alteração/remoção no carrinho, nova
  revisão após reajuste, resposta perdida recuperada sem duplicar pedido,
  cancelamento antes do preparo e encerramento sem cobrança.
- PWA: nenhum erro de manifesto ou instalabilidade pelo Chrome; SW ativo, página
  offline, cardápio salvo legível, POST sem rede bloqueado e nenhum dado privado no cache.

Evidências brutas ficam em `.tmp/browser-result.json`, `.tmp/browser-regressions.json`,
`.tmp/pwa-result.json` e `.tmp/screens/`, fora do versionamento. Os scripts para
reprodução estão versionados e descritos em [VALIDACAO_NAVEGADOR.md](VALIDACAO_NAVEGADOR.md).

## Conferência dos requisitos funcionais

Estado: **validado** significa evidência técnica no código, testes e/ou navegador,
dentro dos limites acima; não afirma demonstração em hardware físico.

| Requisito | Resultado / evidência |
| --- | --- |
| RF01 | Validado: QR com UUID, identificação da mesa e abertura real do cardápio |
| RF02 | Validado: cadastro no admin e download de PNG autenticado pela interface |
| RF03 | Validado: garçom abre sessão; pagamento ou encerramento sem cobrança a fecha |
| RF04 | Validado: mapa mostra livre, ocupada e aguardando conta, com polling |
| RF05 | Validado: categorias, fotos, descrições e preços; fotos funcionam com DEBUG=False |
| RF06 | Validado: quantidade, adicionais e observações do item pelas telas |
| RF07 | Validado: indisponível é sinalizado/bloqueado; mudança chega ao cliente e servidor revalida |
| RF08 | Validado: carrinho, alteração de quantidade e remoção no navegador |
| RF09 | Validado: cálculo decimal no servidor e totais da revisão/conta |
| RF10 | Validado: revisão e confirmação; reajuste exige nova confirmação e pode reverter envio |
| RF11 | Validado: vários pedidos na sessão, chaves distintas; repetição da mesma tentativa não duplica |
| RF12 | Validado: acompanhamento do cliente por polling de quatro segundos |
| RF13 | Validado: colunas de cozinha com mesa, itens, extras e observações |
| RF14 | Validado: aceitar/iniciar preparo é uma ação conjunta; próximo passo é pronto |
| RF15 | Validado: cozinha altera disponibilidade pela tela e API protegida |
| RF16 | Validado: novos pedidos aparecem no painel sem recarga manual |
| RF17 | Validado: garçom vê prontos, marca a caminho e confirma entrega |
| RF18 | Validado: solicitações de conta aparecem no painel do garçom |
| RF19 | Validado: conta contém os pedidos da sessão; cancelados não são cobrados |
| RF20 | Validado: cliente e garçom podem solicitar conta, sem fechar enquanto há pendências |
| RF21 | Validado: testes de Pix/cartão/dinheiro e pagamento por cartão na interface |
| RF22 | Validado: aprovação, conta e encerramento atômicos; mesa livre e cliente atualizado |
| RF23 | Validado: CRUD admin/API, preço não negativo e exclusões históricas protegidas |
| RF24 | Validado: administrador comum cadastra equipe/perfil, sem se tornar superusuário |
| RF25 | Validado: pedidos e contas pagas consultáveis; datas/intervalos inválidos retornam 400 |

## Conferência dos requisitos não funcionais

| Requisito | Resultado / evidência |
| --- | --- |
| RNF01 | Manifesto, ícones e SW; Chrome sem erro de instalabilidade. Instalação física a demonstrar |
| RNF02 | Página offline e cardápio salvo testados com rede desligada no navegador |
| RNF03 | Viewports móvel/tablet/monitor testados; grid móvel corrigido para não ampliar a tela |
| RNF04 | Polling de quatro segundos em cliente/cozinha/garçom, com recuperação de falhas |
| RNF05 | Link aleatório, PNG restrito a admin e diretório de QR sem rota pública |
| RNF06 | Perfis e contexto mesa/sessão, isolamento, CSRF e admin protegidos por regressões |
| RNF07 | CSRF também anônimo, senhas Django com hash, segredos ignorados pelo Git |
| RNF08 | Snapshots do produto e adicionais preservados após alteração do cardápio |
| RNF09 | Fetch e API REST; schema completo validado sem erros/avisos |
| RNF10 | Regras críticas testadas em PostgreSQL; SQLite só na configuração rápida explícita |
| RNF11 | `.env` e `.env.example`, banco/usuário próprios, sem segredos de uso no repositório |
| RNF12 | README reproduzível, versões fixadas, migrations, seed repetível e scripts de validação |
| RNF13 | pt-BR, BRL e horários explícitos de São Paulo nas telas operacionais |

## Conferência das regras essenciais

| Regra | Resultado / evidência |
| --- | --- |
| RN01 | Matriz das 36 combinações: somente sequência obrigatória e cancelamento inicial permitidos |
| RN02 | Cancelamento somente em RECEBIDO; cozinha tem ação com confirmação antes do preparo |
| RN03 | Histórico inicial e transições com horário/autor; falha reverte alteração e histórico |
| RN04 | Pedido só é criado com mesa ativa e sessão aberta, revalidada sob lock |
| RN05 | Constraint de sessão única e corrida real com duas aberturas |
| RN06 | Decimal: `(preço do produto + adicionais) × quantidade` |
| RN07 | Referência de R$ 41,90 e quantidade 2 igual a R$ 83,80 verificada |
| RN08 | Produto indisponível, inclusive no carrinho antigo, rejeita o pedido inteiro |
| RN09 | Pagamento/encerramento rejeita pendentes; admin não pode contornar por edição |
| RN10 | Sessão encerrada rejeita novos pedidos e requisições antigas; corrida não reativa conta paga |

As regras operacionais vivem em `restaurante/services/`; API e ações do admin
compartilham os serviços. Nenhum estado extra foi adicionado ao fluxo obrigatório.

## Conferência de stack, escopo e entregáveis

- Python 3, Django, DRF, PostgreSQL, psycopg 3, qrcode/Pillow e django-environ.
- Dependências diretas fixadas com `==`; Bootstrap 5.3.8 local, HTML/CSS/Fetch,
  manifesto, service worker e Cache API. Nenhuma dependência de Node no servidor.
- Banco/usuário próprios e migrations reais. `seed_data` pode ser repetido sem
  redefinir cadastros/senhas; usuários demonstrativos são uma opção explícita.
- Um restaurante. Sem multi-tenant, gateway real, comandas ou nota fiscal.
- WebSocket, divisão de conta, lançamento pelo garçom, relatórios, setores e estoque
  não foram escolhidos; não são apresentados como funcionalidades do MVP.
- Planejamento, esboços, divisão sugerida da dupla, README, API e prompts estão no repo.
  A dupla precisa preencher seus nomes/datas reais e saber explicar o código.
- Etapas 1–5 foram commitadas e enviadas individualmente; etapa 6 contém esta
  validação e as correções encontradas no uso real do navegador.

## Roteiro de aceite presencial ainda necessário

1. Disponibilizar a aplicação em HTTPS alcançável pelos dois aparelhos. Configurar
   PUBLIC_BASE_URL, ALLOWED_HOSTS e CSRF_TRUSTED_ORIGINS; gerar o QR desse endereço.
2. Abrir sessão no garçom; no celular, escanear QR, montar item com extras/observação
   e revisar. Na segunda tela, mostrar o pedido chegando à cozinha por polling.
3. Demonstrar recebido → em preparação → pronto → a caminho → entregue, com
   histórico no admin. Tentar salto e cancelamento tardio: ambos devem ser rejeitados.
4. Enviar outro pedido na mesma sessão e mostrar conta acumulada; solicitar conta,
   escolher meio simulado e liberar mesa. Reenvio de sessão antiga deve falhar.
5. Instalar no celular, desligar conexão, navegar e mostrar página offline/cardápio
   salvo sem permitir envio. Reconectar e conferir dados atuais.
6. Apresentar README, testes, migrations, schema, prompts e contribuição da dupla.

Docker/Gunicorn Linux é infraestrutura recomendada, preparada mas não executada
neste ambiente Windows. A execução local com PostgreSQL real foi validada.
