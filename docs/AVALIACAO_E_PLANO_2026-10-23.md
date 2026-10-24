# MesaFácil — avaliação e plano de execução

Data: 23/10/2026. Escopo desta etapa: atualizar, avaliar e planejar. Nenhuma correção
ou funcionalidade deste plano foi implementada durante a avaliação.

## 1. Versão avaliada e preservação do trabalho

- Repositório: `MHzin15/MesaFacil---Trabalho-Back-End`, branch `main`.
- `git pull --ff-only` concluído: `0ba5126` → `7c6ce3ad0af9cb1295b9af05d763ee2febfb24ed`.
- A base local anterior não estava commitada. O primeiro pull recusou sobrescrevê-la.
- Ela foi preservada integralmente com arquivos não rastreados no stash
  `56dd2776f2265103c4c62e7af768b9354e9dd7da`, mensagem
  `MesaFacil base local preservada antes do pull e auditoria 2026-10-23`.
- O stash não foi aplicado nem removido. A avaliação considera o código remoto atualizado,
  sem misturar os apps antigos `menu`/`tables` com o app atual `restaurante`.
- `.env` e `.venv` locais foram mantidos. A configuração antiga do `.env` tem
  `POSTGRES_*`, enquanto o código atualizado exige `DATABASE_URL`.

O stash pode mudar de posição ao criar novos stashes; seu hash acima identifica a cópia.
Na execução, reaproveitar seletivamente o que for útil, sem aplicar o stash inteiro
por cima da arquitetura atual e sem duplicar modelos ou migrations.

## 2. Resultado da avaliação

O projeto está mais avançado que a base anterior, mas ainda não cumpre o MVP completo.
Existe uma implementação significativa de pedidos, sessões, preços históricos,
auditoria e painéis do cliente/cozinha. O garçom tem API sem página funcional;
o pagamento tem backend sem interface operacional; o PWA ainda não foi implementado.

### Verificações executadas

| Verificação | Resultado e limite |
| --- | --- |
| Instalação isolada do `requirements.txt` | Sucesso em Python 3.13; Django resolvido como 5.2.18 |
| `python -m pytest -q` | **43 testes aprovados**, em SQLite em memória |
| `pip check` | Nenhuma dependência quebrada |
| `check` com configuração de testes | Sem problemas de configuração |
| `makemigrations --check --dry-run`, em modo de testes | Nenhuma migration pendente de geração |
| `manage.py check`, configuração normal local | Falha: `DATABASE_URL` não está definido no `.env` preservado |
| OpenAPI com validação e falha em avisos | Falha; 68 ocorrências de erro, 17 erros distintos; 4 avisos, 2 distintos |
| PostgreSQL real | Não validado; Docker/psql não encontrados no PATH desta avaliação |
| Navegador, responsividade e instalação em celular | Não validados nesta etapa; avaliação de frontend por leitura do código |

Os 43 testes incluem 39 testes em `restaurante/tests.py` e quatro testes de páginas.
Os 41 avisos emitidos pela suíte apontam ausência de `staticfiles/`; ainda é necessário
validar `collectstatic` e a execução da aplicação com a configuração final.
O teste existente chamado `test_csrf_e_logout_por_post` não ativa a fiscalização CSRF
do cliente de testes, portanto seu sucesso não comprova a proteção dos endpoints públicos.

As sondagens adicionais foram executadas apenas em banco temporário em memória,
sem alterar o `.env`, banco de aplicação ou código funcional. Os scripts e resultados
locais estão em `.tmp/auditoria/`, diretório ignorado pelo Git.

## 3. Problemas confirmados e prioridades

| Prioridade | Problema / evidência | Correção planejada |
| --- | --- | --- |
| Alta | O admin permite desmarcar `ativa` de uma sessão com pedido RECEBIDO e sem conta paga; POST aceito, sessão encerrada | Tornar campos operacionais protegidos e conduzir ações do admin pelas mesmas regras de negócio da API |
| Alta | `solicitar_conta` lê a sessão e usa `save()` sem bloqueio. Uma leitura anterior ao pagamento pode gravar `ativa=True` de volta | Bloquear a sessão e alterar apenas os campos permitidos dentro da transação; não reabrir sessão paga |
| Alta | Com `APIClient(enforce_csrf_checks=True)`, criação anônima de pedido sem token retorna 201; solicitação de conta sem token retorna 200 | Exigir CSRF também nas escritas do cliente sem login, com sessão anônima e testes reais de cookie/token/origem |
| Alta | QR é salvo com nome previsível em mídia pública: `/media/qrcodes/mesa_1_qrcode.png`; download anônimo retornou 200 em desenvolvimento | Servir o PNG por endpoint autenticado, sem deixar o QR acessível pelo diretório público de mídia; preservar o URL do cliente com UUID aleatório |
| Alta | `TESTING` troca automaticamente o banco por SQLite, inclusive em `manage.py test` com `DATABASE_URL` de PostgreSQL | Separar configuração de testes rápidos da de integração e permitir executar as regras críticas e concorrência em PostgreSQL real |
| Alta | `/painel/` do garçom redireciona para `/garcom/`, mas essa rota responde 404 | Implementar página, proteção por perfil, mapa de mesas, entregas, contas e pagamento |
| Média | Gerador de schema não infere serializers de 17 views; ter Swagger configurado não comprova contratos documentados | Declarar entradas, saídas, erros, parâmetros e permissões; regenerar e validar com modo estrito |
| Média | Cadastro de produto com preço `-1.00` retorna 201 | Validadores em serializers/admin/modelos e constraints no banco para valores e quantidades válidos |
| Média | `data_inicio=nao-e-data` na consulta administrativa retorna 500 | Serializer de filtros com datas válidas e intervalo consistente, resposta 400 para entradas inválidas |
| Média | O frontend do cliente consulta disponibilidade no carregamento e após erro, enquanto a cozinha pode alterá-la depois | Atualizar disponibilidade no polling e revalidar o carrinho antes do envio; manter validação definitiva no servidor |
| Média | Criação usa apenas o UUID e escolhe a sessão ativa atual; uma requisição antiga pode acabar em uma sessão recém-aberta | Enviar e validar a sessão esperada, recusando pedidos de uma sessão já encerrada, mesmo após reabertura da mesa |
| Média | `Perfil.role=ADMIN` é separado de `is_staff` e permissões Django; `/painel/` encaminha ao admin sem configurar esses direitos | Definir e testar provisionamento de cada perfil, inclusive administrador sem privilégios de superusuário |
| Média | Conta do cliente exclui cancelados da listagem e consulta administrativa de contas não restringe explicitamente a contas pagas | Mostrar todos os pedidos com cancelados sem cobrança; filtrar contas fechadas explicitamente |
| Média | `.env.example` usa o usuário genérico `postgres`; o ambiente local preservado tem formato incompatível | Banco e usuário próprios do projeto, configuração reproduzível e migração local de configuração sem publicar segredos |
| Média | Dependências usam intervalos; Django limitado a 5.2, django-filter a 24.x e gunicorn a versões abaixo de 23 | Conferir releases estáveis atuais, atualizar o conjunto compatível e fixar versões exatas com `==` |
| Média | README afirma PWA e lista contratos/migrations diferentes do código | Reescrever conforme estado real, nomes reais de migrations e passos verificados em instalação limpa |

A corrida de `solicitar_conta` foi reproduzida por interleaving controlado: uma
instância da sessão lida antes do pagamento foi devolvida ao endpoint depois do
pagamento; a conta continuou paga e a sessão voltou a ficar ativa. Isso demonstra
o risco de escrita desatualizada; não substitui um teste concorrente em PostgreSQL.

A rota real atual de geração é `/api/mesas/<id>/gerar_qrcode/`, com sublinhado.
O README anuncia `gerar-qrcode`, com hífen. A execução deve escolher um contrato
único e atualizar documentação e consumidores juntos.

## 4. Matriz de requisitos funcionais

Legenda: **Implementado** = código encontrado e coberto pela revisão/suíte dentro
dos limites acima; **Parcial** = faltam integração, proteção, interface ou validação;
**Pendente** = componente obrigatório ausente. Nenhum status equivale à aceitação
final sem demonstração do fluxo em PostgreSQL e dois aparelhos.

| ID | Estado atual | Trabalho necessário para aceite |
| --- | --- | --- |
| RF01 | Parcial | UUID e página de mesa existem; proteger entrega do PNG e validar leitura do QR no celular |
| RF02 | Parcial | Geração por API existe; integrar ação/download protegido ao admin e imprimir o próprio QR, se desejado |
| RF03 | Parcial | APIs de abrir/fechar existem; completar interface do garçom e impedir encerramento irregular pelo admin |
| RF04 | Parcial | Estados livre/ocupada/aguardando conta existem na API; apresentar mapa no garçom com polling |
| RF05 | Implementado | Categorias, foto, descrição e preço no cliente; verificar imagens e layout no celular |
| RF06 | Implementado | Quantidade, adicionais e observação por item presentes; validar fluxo em navegador |
| RF07 | Parcial | Bloqueio no backend e botão desabilitado existem; sincronizar mudanças de disponibilidade com cliente/carrinho |
| RF08 | Implementado | Carrinho permite alterar quantidades e remover itens; verificar persistência e mudança de sessão |
| RF09 | Implementado | Fórmula e snapshots presentes; preservar Decimal no servidor e consistência dos totais na revisão |
| RF10 | Implementado | Revisão e confirmação existem; validar comportamento de erro e evitar reenvio duplicado |
| RF11 | Implementado | Vários pedidos associados à sessão; validar isolamento após fechamento e nova abertura |
| RF12 | Implementado | Cliente acompanha pedidos por polling de quatro segundos; verificar recuperação após perda de conexão |
| RF13 | Implementado | Cozinha agrupa três estados com mesa, itens, adicionais e observações |
| RF14 | Implementado | Aceitar/iniciar preparo é uma ação conjunta; marcar pronto é a próxima; manter a sequência obrigatória |
| RF15 | Implementado | Endpoint e interface de disponibilidade da cozinha presentes |
| RF16 | Implementado | Cozinha consulta automaticamente em quatro segundos; validar chegada de pedido no segundo aparelho |
| RF17 | Parcial | API de prontos/a caminho existe; criar ações na página do garçom com permissões e atualização automática |
| RF18 | Parcial | API identifica solicitações de conta; criar seção e sinalização no garçom |
| RF19 | Parcial | Conta acumulada no cliente; incluir também cancelados na apresentação sem cobrar seus valores |
| RF20 | Parcial | Botão do cliente e API existem; incluir ação do garçom e corrigir CSRF/corrida com pagamento |
| RF21 | Parcial | Backend aceita Pix/cartão/dinheiro; criar seleção e confirmação na interface do atendimento |
| RF22 | Parcial | Backend aprova e encerra sessão; completar interface e proteger concorrência/repetição/alterações no admin |
| RF23 | Parcial | CRUD pelo admin/API existe; bloquear valores inválidos e tratar exclusões protegidas sem erro 500 |
| RF24 | Parcial | Usuários e Perfil existem; consolidar associação de papel, acesso ao admin e permissões necessárias |
| RF25 | Parcial | Consultas administrativas existem; validar filtros, datas, contas pagas e exposição na área administrativa |

## 5. Matriz de requisitos não funcionais

| ID | Estado atual | Trabalho necessário para aceite |
| --- | --- | --- |
| RNF01 | Pendente | Manifesto, ícones adequados, service worker registrado e instalação demonstrada |
| RNF02 | Pendente | Página offline real e política de cache; o aviso de conexão atual não basta |
| RNF03 | Parcial | HTML/CSS responsivos presentes; validar celular, tablet e monitor, inclusive garçom |
| RNF04 | Parcial | Polling cliente/cozinha implementado; completar garçom e recuperação de erro inicial/conexão |
| RNF05 | Parcial | UUID aleatório existe; QR público com nome previsível permite recuperar o token |
| RNF06 | Parcial | Permissões por papel existem; cobrir todos os endpoints, admin, recursos de outras mesas e sessões anteriores |
| RNF07 | Parcial | Login com hash e `.env` existem; corrigir CSRF anônimo e configuração de cookies/origens para HTTPS |
| RNF08 | Implementado | Produto e adicionais têm preço copiado nos itens; testes verificam preservação após reajuste |
| RNF09 | Parcial | Frontend usa Fetch e API REST; schemas de endpoints críticos estão incompletos |
| RNF10 | Parcial | 43 testes passam; faltam regressões dos problemas encontrados, pagamento completo e concorrência em PostgreSQL |
| RNF11 | Parcial | `.env.example` existe; alinhar configuração nova, banco/usuário próprios e manter segredos fora do Git |
| RNF12 | Parcial | README e seed existem; corrigir divergências e verificar instalação limpa com PostgreSQL |
| RNF13 | Implementado | pt-BR, timezone São Paulo e BRL presentes; verificar datas e valores em todas as telas novas |

## 6. Matriz de regras de negócio

| ID | Estado atual | Critério de aceite da execução |
| --- | --- | --- |
| RN01 | Implementada na API | Matriz completa das transições, sem saltos, regressões ou repetição de estado |
| RN02 | Implementada na API | Cancelamento apenas em RECEBIDO; cozinha/garçom/admin conforme permissão definida |
| RN03 | Implementada na API | Evento inicial e toda transição com data/hora/autor; anônimo identificado como cliente; rollback em falha |
| RN04 | Implementada na API | Pedidos somente com mesa ativa e sessão aberta/autorizada, incluindo cenários concorrentes |
| RN05 | Constraint presente | Uma sessão ativa por mesa no banco e teste com duas conexões PostgreSQL reais |
| RN06 | Implementada na API | `(preço unitário + soma de adicionais) × quantidade`, calculado com Decimal no servidor |
| RN07 | Testada | R$ 32,90 + R$ 5,00 + R$ 4,00 = R$ 41,90; quantidade 2 = R$ 83,80 |
| RN08 | Implementada na API | Produto indisponível rejeitado mesmo se estiver no carrinho; pedido inteiro revertido em erro |
| RN09 | Parcial | API bloqueia pendentes; admin e demais canais precisam obedecer à mesma regra, com testes de pagamento |
| RN10 | Parcial | Bloqueio da sessão fechada existe; impedir reativação por escrita desatualizada e pedido antigo na sessão nova |

## 7. Decisões para a implementação

1. Continuar com o app `restaurante`, aproveitando o código válido. Não recomeçar o projeto.
2. Restaurante único; não criar multi-tenant, gateway real, impressão de comandas ou nota fiscal.
3. Priorizar todo o MVP. WebSocket, divisão da conta, pedido pelo garçom, relatórios,
   setores da cozinha e estoque ficam explicitamente fora desta execução inicial.
4. Usar polling em poucos segundos. Channels/Redis/Daphne só entram se o opcional
   de tempo real for escolhido depois do MVP aprovado.
5. Preservar exatamente os estados RECEBIDO → EM_PREPARACAO → PRONTO → A_CAMINHO → ENTREGUE.
   CANCELADO é terminal e só parte de RECEBIDO. Aceitar/iniciar preparo continua
   uma ação conjunta; não inventar um estado intermediário que altere a sequência.
6. Centralizar operações de negócio em serviços dentro de `restaurante/services/`:
   abrir sessão, criar pedido, mudar status, solicitar conta, aprovar pagamento e
   encerrar sessão. Views e ações do admin devem chamá-los.
7. PostgreSQL é o banco da aplicação e da validação final. SQLite pode existir
   apenas em configuração explicitamente selecionada para testes rápidos.
8. Anônimo entra pelo UUID do QR, obtém o contexto da mesa/sessão e CSRF; consultas
   e escritas devem validar esse contexto. Não usar IDs numéricos como autorização.
   A mesa pode reabrir com o mesmo QR, mas requisições da sessão anterior não podem
   operar na nova sessão sem uma atualização explícita do contexto.
9. Manter preços copiados dos produtos/adicionais e totais canônicos no servidor.
   Padronizar valores monetários na API com duas casas decimais e formato documentado.
10. Serializar operações concorrentes com locks de sessão em ordem consistente,
    preservando a constraint de sessão ativa. Proteger também mudanças de disponibilidade.
11. Pagamento é simulado e executado pelo garçom/admin: Pix, cartão ou dinheiro.
    Só aprova com todos os pedidos entregues/cancelados. Aprovação, conta e fechamento
    devem ocorrer atomicamente; repetição não pode duplicar cobrança nem reabrir sessão.
12. Pode solicitar a conta antes do fim do preparo; isso sinaliza o atendimento,
    sem permitir aprovação do pagamento enquanto houver pendências. Não acrescentar
    bloqueio de novos pedidos após mera solicitação como se fosse exigência do enunciado.
13. Sessão vazia ou com pedidos todos cancelados pode ser encerrada sem cobrança,
    desde que não haja pendências; documentar e testar esse caso explicitamente.
14. PWA nunca enfileira pedidos/pagamentos offline. Pode guardar recursos estáticos
    e cardápio já carregado; não guardar conta, pedidos ou respostas da equipe em cache.
15. Usuários demonstrativos serão explícitos para ambiente de demonstração; não
    criar superusuário de senha pública automaticamente em uma instalação normal.

## 8. Plano em etapas pequenas, com critérios de saída

### Etapa 1 — Ambiente reproduzível e critérios consolidados (marcos 1–2)

- Guardar esta matriz como checklist; manter esboços e divisão da dupla no README.
- Adaptar a configuração local para `DATABASE_URL` sem substituir segredos existentes.
- Criar banco e usuário próprios do MesaFácil e oferecer Compose para Django + PostgreSQL,
  mantendo também instruções de execução local no Windows.
- Consultar releases estáveis oficiais na data da implementação; atualizar o conjunto
  compatível e fixar todas as dependências diretas com `==`. Atualizar requisito de Python.
- Justificar pacotes extras no README; manter Bootstrap 5 e Fetch.
- Separar configurações de testes rápidos e testes PostgreSQL; impedir SQLite na entrega.
- Aplicar migrations em banco PostgreSQL vazio e verificar caminho de atualização.
- Validar seed repetível, imagens de exemplo e provisionamento explícito dos usuários.

**Saída:** instalação limpa seguindo o README, banco conectado, migrations e seed
executados; suíte atual aprovada no ambiente configurado. Sem executar a fase seguinte
com um ambiente que só funciona em SQLite.

### Etapa 2 — Integridade e segurança antes da expansão (marcos 2–3)

- Extrair serviços de negócio mantendo os contratos necessários à interface existente.
- Corrigir fechamento pelo admin, reativação por escrita desatualizada e contexto
  de sessão esperada na criação de pedidos.
- Exigir CSRF em toda escrita do cliente/equipe, com proteção de origem adequada.
- Proteger o download do QR fora da mídia pública e integrar geração ao admin.
- Consolidar perfis, permissões Django e ações permitidas a cozinha/garçom/admin.
- Acrescentar constraints/validadores de preço, quantidade e número de mesa.
- Tratar datas inválidas e exclusões protegidas com respostas de erro documentadas.

**Saída:** reproduções da seção 3 viram testes de regressão que passam com a correção;
matriz RN01–RN10 e de permissões aprovada em PostgreSQL; nenhum canal do admin contorna
o pagamento ou os estados. Verificar explicitamente acesso a outra mesa e a sessão anterior.

### Etapa 3 — Contratos da API e conclusão do cliente/cozinha (marco 3)

- Anotar todos os endpoints com schemas de entrada/saída, erros e permissões.
- Padronizar tipos monetários, datas, respostas vazias e filtros. Não documentar
  um serializer de pedido como resposta agrupada de cozinha sem schema correspondente.
- Corrigir divergências entre README e rotas reais, inclusive QR.
- Revalidar carrinho, disponibilidade e contexto da sessão antes do envio.
- Recuperar polling após erro no carregamento inicial e reconexão, sem loops simultâneos.
- Testar revisão, quantidade, adicionais, observações, vários pedidos e histórico.
- Incluir cancelados na conta apresentada sem adicioná-los ao total devido.

**Saída:** `spectacular --validate --fail-on-warn` passa; cliente envia e acompanha
pedido real; cozinha o vê por polling e avança as duas etapas autorizadas.

### Etapa 4 — Garçom, conta e pagamento (marco 4)

- Implementar `/garcom/` com login e perfil correto; corrigir o destino após login.
- Exibir mapa de mesas, abrir sessão, listar prontos/a caminho e confirmar entrega.
- Mostrar solicitações de conta e permitir solicitação pelo garçom.
- Revisar conta com todos os pedidos e selecionar Pix/cartão/dinheiro no atendimento.
- Aprovar pagamento simulado por serviço transacional e liberar a mesa.
- Refletir fechamento no cliente e no salão; impedir pedidos/cobranças repetidos.
- Completar consulta administrativa de pedidos e contas pagas com filtros por data.

**Saída:** ciclo QR → pedido → cozinha → a caminho → entregue → conta → pagamento
→ mesa livre funciona sem chamada manual de API; cliente não precisa de login.

### Etapa 5 — PWA e offline (marco 4)

- Criar manifesto, ícones, `start_url`, escopo e registro do service worker.
- Garantir que o service worker tenha o escopo necessário às páginas da aplicação.
- Criar página offline e política de atualização dos caches.
- Cachear somente recursos públicos permitidos; manter pedidos/conta/equipe e
  escritas fora do cache e de qualquer fila offline.
- Exibir reconexão e atualização segura do cardápio; manter contexto correto da mesa.
- Validar instalação por HTTPS ou localhost; para celular usar endereço HTTPS alcançável.

**Saída:** aplicação instalável demonstrada no celular; uma navegação sem conexão
recebe página amigável; nenhum pedido é considerado enviado enquanto estiver offline.

### Etapa 6 — Aceitação final, documentação e demonstração (marco 5)

- Executar testes de unidade, API, regressão e transações concorrentes em PostgreSQL.
- Verificar admin, filtros, permissões, CSRF, QR, upload de fotos e snapshots financeiros.
- Validar interface em celular/tablet/monitor, teclado e mensagens em pt-BR.
- Conferir `collectstatic`, mídia e execução de produção; usar Gunicorn em ambiente
  Linux/container, mantendo execução local compatível com Windows.
- Atualizar README com comandos realmente testados, dados e usuários demonstrativos.
- Guardar prompts adaptados por etapa e cada erro de regra/correção em `docs/prompts/`.
- Ensaiar com dois aparelhos: cliente no celular e equipe na segunda tela, até liberar a mesa.
- Encerrar cada marco com commit e demonstração curta; datas dependem do professor.

**Saída:** todos os RF01–RF25, RNF01–RNF13 e RN01–RN10 aprovados por evidência;
checklist sem itens obrigatórios pendentes. Opcionais só depois dessa aprovação.

## 9. Testes obrigatórios a acrescentar na execução

- Escrita anônima com/sem CSRF, token inválido, origem indevida e sessão expirada.
- Isolamento entre mesas e entre sessões; pedido atrasado após fechamento/reabertura.
- Duas aberturas simultâneas e pedido concorrente com fechamento/pagamento.
- Solicitação de conta concorrente com pagamento: sessão paga permanece encerrada.
- Duas mudanças simultâneas do mesmo pedido: uma transição válida e um histórico por etapa.
- Pagamento com cada estado pendente: rejeitar; todos entregues/cancelados: aprovar.
- Três meios de pagamento; meio inválido; repetição; sessão vazia; conta só com cancelados.
- Falha no fechamento ou gravação da conta: rollback completo, sem pagamento parcial.
- Admin não fecha ou reativa sessão irregularmente nem altera preços históricos de pedidos.
- Filtros de datas válidos, inválidos, intervalo invertido e limites do dia em São Paulo.
- QR e PNG administrativo protegidos; link UUID funciona sem enumerar mesas.
- Seed repetido não sobrescreve dados, preços, senhas nem perfis existentes indevidamente.
- PWA instalado, navegação offline, reconexão e ausência de cache/filas de dados privados.

## 10. Referências técnicas para decisões de versão e segurança

- [Django no PyPI](https://pypi.org/project/Django/): versão estável e requisito de Python.
- [django-filter no PyPI](https://pypi.org/project/django-filter/): releases e compatibilidade.
- [Gunicorn no PyPI](https://pypi.org/project/gunicorn/): releases e execução em Unix.
- [DRF — SessionAuthentication](https://www.django-rest-framework.org/api-guide/authentication/#sessionauthentication):
  a proteção CSRF padrão dessa autenticação é aplicada às requisições autenticadas;
  o fluxo anônimo precisa de proteção explícita, como confirmado pelas sondagens locais.

Próxima ação proposta, quando a implementação for solicitada: executar **Etapa 1**,
sem avançar automaticamente a opcionais nem considerar os 43 testes atuais como aceite do MVP.
