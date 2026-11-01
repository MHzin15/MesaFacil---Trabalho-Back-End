# Auditoria de segurança, performance e manutenibilidade — 01/11/2026

## Escopo e método

Revisão do backend Django/DRF, modelos, serviços transacionais, permissões,
admin, autenticação, templates, JavaScript, PWA, scripts, dependências e
configuração Docker/Render. Foram examinados os 136 arquivos originalmente
rastreados e 355 blobs do histórico Git, distribuídos em 29 commits, com buscas
de padrões de credenciais. Isso não certifica ausência de segredos arbitrários.
O `.env` pessoal não foi reproduzido no relatório e a alteração pré-existente em
`docs/DEMONSTRACAO.md` foi preservada.

Ferramentas: testes Django/pytest, PostgreSQL e SQLite, Bandit 1.9.4, pip-audit
2.10.1, `pip check`, checks do Django e validação estrita do OpenAPI. O scanner
de dependências recebeu nomes/versões públicos de pacotes, não código nem
credenciais da aplicação. Os scanners foram instalados em ambiente separado,
em `.local/security-tools`.

As severidades abaixo são avaliações contextuais, não escores CVSS. As categorias
OWASP são descritas por nome; os identificadores CWE especificam a fraqueza.

## Patches aplicados

### 1. Senhas fracas no cadastro e bootstrap — alta

- **Risco original:** `AUTH_PASSWORD_VALIDATORS` estava vazio. A chamada
  `validate_password()` em `preparar_render` não validava força; o teste existente
  comprovou que `admin123` criava um superusuário. Falha de autenticação, CWE-521.
- **Solução:** ativados os quatro validadores nativos: similaridade com dados do
  usuário, tamanho mínimo, senha comum e senha inteiramente numérica.
- **Impacto:** validação somente ao definir novas senhas nos fluxos que usam os
  validadores; autenticação, hashes e senhas existentes permanecem válidos.
  Nenhuma senha de usuário foi redefinida. `create_user()` direto continua com a
  semântica nativa do Django, sem validação automática.
- **Arquivos:** `core/settings.py`; regressões em `restaurante/test_audit.py` e
  teste pré-existente em `restaurante/test_render.py`.

### 2. Tentativas ilimitadas de login — média

- **Risco original:** `/entrar/` e `/admin/login/` não limitavam tentativas,
  permitindo força bruta e gasto repetido com hashes de senha. CWE-307/CWE-400.
- **Solução:** middleware com contadores atômicos no PostgreSQL, compartilhados
  entre workers e entre os dois logins. Padrões: 20 tentativas por conta e 100
  por endereço remoto em janelas fixas de 300 segundos; excesso retorna HTTP 429
  e `Retry-After`. A chave da conta usa normalização Unicode NFKC e casefold.
  Os contadores armazenam HMAC, sem usuário/IP em texto puro. Entradas vencidas
  são removidas nas próximas tentativas. CSRF é verificado antes do contador.
- **Impacto:** uma tabela adicional, `LoginRateBucket`, criada pela migração
  `0006`; poucas consultas somente nos POSTs de login. A contagem inclui
  tentativas bem-sucedidas e malsucedidas. GETs, sessões já autenticadas e fluxos
  de pedidos não consomem essa cota. Login normal mantém o redirecionamento.
- **Operação:** `LOGIN_RATE_LIMIT_WINDOW`, `LOGIN_RATE_LIMIT_ACCOUNT` e
  `LOGIN_RATE_LIMIT_IP` aceitam inteiros positivos via ambiente. Não se confia
  em `X-Forwarded-For` arbitrário; atrás de proxy, `REMOTE_ADDR` pode representar
  o proxy compartilhado. Dimensionar a cota de IP para essa topologia. Janelas
  fixas permitem rajadas na mudança de janela, e bloqueios por conta podem ser
  provocados por terceiros; o limite é temporário. Proteção de borda continua
  apropriada contra ataques distribuídos e volumétricos.
- **Arquivos:** `restaurante/middleware.py`, `models.py`, migração `0006`,
  `core/settings.py`; testes de limites, expiração, Unicode, CSRF e concorrência.

### 3. Contas demonstrativas em produção — alta se o comando fosse usado

- **Risco original:** `seed_data --demo-users` aceitava execução com `DEBUG=False`
  e criava usuários com senhas públicas, inclusive superusuário. CWE-798.
- **Solução:** o comando rejeita essa combinação antes de escrever qualquer
  dado. A opção explícita continua disponível em demonstração local com
  `DEBUG=True`; o seed sem usuários continua disponível em produção.
- **Impacto:** sem alteração de usuários existentes, catálogo, preços ou UUIDs.
  A guarda não substitui desligar DEBUG em qualquer ambiente exposto nem troca
  senhas demonstrativas já criadas anteriormente.
- **Arquivos:** `restaurante/management/commands/seed_data.py` e testes.

### 4. Ferramenta de instalação vulnerável e pacotes desatualizados

- **Risco original:** `pip 25.2` no ambiente local recebeu 12 entradas do catálogo,
  correspondentes a **seis avisos distintos**, relacionados à instalação e
  extração de pacotes. São riscos da cadeia de instalação, não seis falhas HTTP
  da aplicação. Componentes vulneráveis, CWE-22 nos avisos de travessia de paths.
- **Solução:** `pip 26.2.2` instalado no ambiente local e fixado no bootstrap
  documentado, Dockerfile e build do Render, antes da instalação da aplicação.
  Atualizadas também as versões disponíveis de `pytest 9.1.1 → 9.2.0`,
  `asgiref 3.12.1 → 3.13.0`, `sqlparse 0.6.0 → 0.6.1` e
  `tzdata 2026.5 → 2026.6`. Estas quatro eram atualizações de manutenção,
  sem vulnerabilidade apontada na consulta inicial; foram fixadas em
  `requirements.txt` e submetidas à suíte novamente.
- **Impacto:** sem atualização de versão principal do Django/DRF e sem mudança
  intencional nas regras de negócio. `tzdata` atualiza regras de fusos globais;
  o sistema continua configurado para `America/Sao_Paulo`.
- **Resultado:** a consulta final das 30 distribuições locais e de Gunicorn
  26.2.0 retornou zero vulnerabilidades conhecidas. A consulta de Gunicorn foi
  explícita, pois seu marcador de plataforma impede instalação no Windows.
  Ela não equivale à execução de um container Linux nem à auditoria de seus
  pacotes de sistema.
- **Evidência:** [resultado do pip-audit](evidencias/PIP_AUDIT_2026-11-01.json).
  Ferramentas opcionais fixadas em `requirements-security.txt`.

| Aviso distinto no pip anterior | CVE | Versão de correção informada pelo catálogo |
| --- | --- | --- |
| PYSEC-2026-1795 | CVE-2025-8869 | 25.3 |
| PYSEC-2026-1796 | CVE-2026-1703 | 26.0 |
| PYSEC-2026-2875 | CVE-2026-3219 | 26.1 |
| PYSEC-2026-2876 | CVE-2026-6357 | 26.1 |
| PYSEC-2026-196 | CVE-2026-8643 | 26.1.2 |
| PYSEC-2026-3721 | CVE-2026-13346 | 26.2 |

O primeiro aviso depende do fallback de extração em versões antigas do Python;
o Python 3.13 deste projeto já mitiga essa condição específica. Os demais
também dependem dos respectivos cenários de pacotes/índices maliciosos descritos
no catálogo. Os avisos não foram tratados como prova de exploração.

O Django já estava em 6.1.2, versão publicada como correção de segurança no
[comunicado oficial de 06/10/2026](https://www.djangoproject.com/weblog/2026/oct/06/security-releases/).
Foi mantido nessa versão. A base consultada pelo scanner é o
[catálogo público do PyPI](https://docs.pypi.org/api/json/).

### 5. HTTPS fora do Render — média

- **Risco original:** apenas o bloco específico do Render forçava HTTPS;
  outros ambientes com `DEBUG=False` não redirecionavam HTTP. Não havia HSTS.
  Configuração insegura de transporte, CWE-319.
- **Solução:** redirecionamento HTTPS por padrão quando `DEBUG=False`,
  independentemente do provedor; HSTS de uma hora no mesmo cenário. Valores
  configuráveis por `SECURE_SSL_REDIRECT` e `SECURE_HSTS_SECONDS`. Desenvolvimento
  com DEBUG e configurações explícitas de testes preservam HTTP local.
- **Impacto:** ambientes publicados precisam oferecer TLS. O reconhecimento de
  `X-Forwarded-Proto` continua limitado ao Render; outros proxies exigem uma
  configuração confiável própria, evitando confiar em cabeçalhos do cliente.
  HSTS de subdomínios/preload não foi ativado sem conhecer o domínio inteiro.
- **Arquivos:** `core/settings.py`, `core/test_settings.py`, testes de deploy.

### 6. JSON excessivamente aninhado — baixa

- **Risco original:** a profundidade podia provocar `RecursionError` no decoder,
  escapando como erro interno em vez de rejeição da entrada. CWE-248/CWE-20.
- **Solução:** `SafeJSONParser` transforma esse caso em erro HTTP 400.
- **Impacto:** não copia o corpo novamente nem muda JSON válido, multipart ou
  formulários. A versão instalada do DRF **já respeita** o limite de bytes do
  Django; essa proteção foi testada e preservada, não reivindicada como uma
  vulnerabilidade nova. Não foi criado um limite arbitrário para itens válidos.
- **Arquivos:** `restaurante/security.py`, `core/settings.py`, testes negativos.

### 7. MIME de mídia e conteúdo ativo — defesa adicional

- **Risco original:** a rota de fotos inferia `Content-Type` da extensão. Um
  arquivo legado ou importado diretamente, com imagem e HTML na extensão `.html`,
  era servido como HTML na origem da aplicação. CWE-79/CWE-434, condicionado à
  presença desse arquivo no armazenamento.
- **Solução:** identifica o MIME pelos bytes com Pillow; conteúdo não reconhecido
  é rejeitado com 404. Respostas de mídia recebem `nosniff` e CSP com `sandbox`
  e `default-src 'none'`. A proteção de paths do Django continua em uso.
- **Impacto:** leitura do cabeçalho da imagem antes de transmitir o arquivo,
  sem recodificação, alteração dos pixels ou carregamento integral da imagem.
  Arquivos inválidos deixam de ser servidos. Não há mudança no upload normal.
- **Limite da evidência:** os formulários e o serializer atuais **já rejeitam**
  `.html`; um teste registra isso. Não foi demonstrado XSS pelo fluxo atual de
  upload. O patch protege arquivos legados/importados e não implica exploração
  por cliente anônimo.
- **Arquivos:** `restaurante/pages.py`, testes com imagem poliglota, arquivo
  inválido e tentativa de travessia de diretório.

### 8. Proteção de variantes de arquivos de ambiente — prevenção

- **Risco original:** apenas `.env` era excluído; `.env.production` e outros
  nomes podiam entrar no Git ou no contexto de build. CWE-540/CWE-200.
- **Solução:** `.gitignore` e `.dockerignore` excluem `.env.*`, preservando
  explicitamente `.env.example`.
- **Impacto:** sem efeito no runtime. Não foi encontrado arquivo de ambiente
  real rastreado nem correspondência de chave privada/token AWS, GitHub ou
  OpenAI nos padrões pesquisados no estado inicial e no histórico. Senhas
  demonstrativas e de testes são públicas e foram classificadas separadamente.
  Não houve rotação nem remoção de credenciais pessoais.

### 9. Consultas N+1 em mesas, pedidos e contas — performance

- **Risco original:** `sessao_ativa` filtrava o related manager a cada acesso,
  ignorando o prefetch de todas as sessões. A serialização consultava relações
  ausentes e o cálculo de contas carregava pedidos, itens e adicionais um a um.
  Isso aumentava a carga no polling e o tempo dentro das transações.
- **Solução:** `MesaQuerySet.com_sessao_ativa()` busca somente sessões abertas
  em lote; `PedidoQuerySet.para_exibicao()` centraliza joins e prefetches de
  itens/adicionais. `SessaoMesa.total_consumo()` faz duas agregações separadas
  para não multiplicar preços quando um item tem vários adicionais. API,
  serviços e admin reutilizam essas consultas.
- **Impacto:** quantidade constante de consultas nos cenários abaixo; totais
  usam `Decimal`, preços gravados, quantidades e exclusão de cancelados.
  Não foram alterados locks, ordem das transições, idempotência ou pagamento.
  O cache de sessões é explícito e restrito aos querysets de leitura; leituras
  transacionais continuam novas e bloqueadas conforme o fluxo original.

| Cenário de regressão | Consultas depois do patch |
| --- | ---: |
| Serializar 10 mesas, cada uma com sessão encerrada e ativa | 2 |
| Serializar 20 pedidos, com três itens e dois adicionais por item | 3 |
| Calcular conta com preços históricos e pedido cancelado | 2 |

Essas contagens são do carregamento/serialização ou cálculo indicado, sem
incluir autenticação e middleware da requisição completa. A suíte não mede
latência de produção nem constitui teste de carga.
As respostas de histórico continuam completas para preservar o contrato atual;
o consumo de memória ainda cresce com o tamanho desses resultados. Uma futura
paginação dos endpoints compostos exige adaptar também os consumidores da API.

### 10. Duplicação e imports implícitos — manutenibilidade

- **Risco original:** consultas repetidas divergiam entre endpoints; import
  wildcard e imports sem uso dificultavam determinar as dependências das views.
- **Solução:** métodos de queryset compartilhados, imports explícitos do schema,
  remoção dos imports sem uso nas views e docstring do serviço na posição correta.
  Os testes de rollback agora injetam a falha em
  `restaurante.services.HistoricoStatusPedido`, onde a gravação realmente ocorre,
  em vez de depender de uma reexportação incidental das views.
- **Impacto:** sem alteração do contrato público; menos pontos de manutenção.
  Não houve uma reescrita geral da aplicação.

## Outras verificações e triagem

- **Autorização/IDOR:** revisados os perfis e os contextos UUID/sessão, com testes
  de mesa alheia, sessão expirada, desativação e separação de funções. O UUID é
  uma credencial de acesso por posse, conforme o desenho existente; compartilhar
  uma foto do QR compartilha esse acesso.
- **Injeção:** queries da aplicação usam ORM; SQL dos scripts usa parâmetros ou
  `psycopg.sql.Identifier`. Não foram identificadas concatenações exploráveis
  de entrada HTTP em SQL, shell, `eval` ou desserialização insegura.
- **XSS/CSRF:** texto dinâmico relevante do frontend usa escaping ou
  `textContent`; templates usam autoescape. Escritas anônimas continuam exigindo
  CSRF. Não se desativou escaping ou CSRF para fazer os testes passarem.
- **Cache/PWA:** respostas privadas permanecem `no-store`; o service worker
  armazena recursos públicos e cardápio, sem pedidos ou contas.
- **Bandit:** a execução final sem testes/migrações registrou 11 alertas:
  três senhas demonstrativas agora protegidas pela guarda de DEBUG; um B104 que
  apenas compara o hostname com `0.0.0.0`, sem abrir socket; sete avisos genéricos
  de subprocess nos scripts locais. Os argumentos destes scripts são listas,
  sem `shell=True`, e não recebem entrada HTTP. Os alertas não foram ocultados
  nem apresentados como 11 vulnerabilidades exploráveis.

## Validação e implantação

A validação inicial tinha 96 testes aprovados, cinco ignorados e uma falha
reproduzível na senha fraca do bootstrap. Os resultados finais estão no registro
de evidências ao final desta seção.

Checks comuns do Django, compatibilidade de pacotes, detecção de migrations
faltantes e schema OpenAPI estrito foram executados. `collectstatic` concluiu.
Em configuração de produção isolada, `check --deploy` mantém apenas W005 e W021:
HSTS para todos os subdomínios e preload dependem de validação da infraestrutura
do domínio. Nenhum alerta foi silenciado.

A migração `restaurante.0006_loginratebucket` foi aplicada no banco local após
verificar que era a única pendente. Ela adiciona apenas a tabela do limitador;
pedidos, contas e usuários existentes não foram modificados pela migração.
Em outros ambientes, aplicar antes de disponibilizar o novo código:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip==26.2.2
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate --noinput
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest --ds=core.settings -q
```

Repetição dos scanners em ambiente separado:

```powershell
python -m venv .local/security-tools
.\.local\security-tools\Scripts\python.exe -m pip install -r requirements-security.txt
.\.local\security-tools\Scripts\python.exe -m pip_audit --path .venv/Lib/site-packages --strict
.\.local\security-tools\Scripts\python.exe -m bandit -r core restaurante scripts -x '*/test_*.py,*/tests.py,*/migrations/*'
```

No Linux, executar também `pip-audit -r requirements.txt` para resolver o conjunto
da plataforma. A evidência desta revisão inclui Gunicorn consultado à parte.
Pins diretos não equivalem a um lock completo com hashes de todos os artefatos.

Não foram executados deploy remoto, scanner de imagem Docker, pentest de uma
instância pública ou ensaio físico em dois aparelhos. A auditoria de fonte,
dependências e testes reduz os riscos identificados; não certifica ausência de
vulnerabilidades futuras ou problemas específicos da infraestrutura publicada.

### Evidências finais

| Verificação | Resultado final |
| --- | --- |
| pytest / PostgreSQL | 118 aprovados, 104 subtestes aprovados, nenhum ignorado; 75,93 s |
| pytest / SQLite | 112 aprovados, 104 subtestes aprovados, seis ignorados por exigirem PostgreSQL; 70,04 s |
| Concorrência no PostgreSQL | Seis cenários aprovados, incluindo limite de login entre workers |
| pip-audit | 31 distribuições consultadas; zero avisos conhecidos |
| Bandit | 2.254 linhas analisadas, zero erros de leitura; 11 alertas triados acima |
| Django check / migrations | Sem problemas nos checks comuns e sem migrations faltantes |
| OpenAPI | Geração com validação e `--fail-on-warn` concluída |
| pip check / collectstatic / git diff --check | Concluídos sem erros |
| Django check --deploy isolado | Apenas W005 e W021, sem silenciamento |

O cluster PostgreSQL local foi iniciado para validar a suíte e aplicar a única
migração pendente; foi encerrado ao final, restaurando o estado inicial.
Não houve commit, push nem deploy remoto.

- [Resumo dos avisos anteriores de dependências](evidencias/PIP_AUDIT_ANTES_2026-11-01.json).
- [Consulta final de dependências](evidencias/PIP_AUDIT_2026-11-01.json).
- [Saída do Bandit para triagem](evidencias/BANDIT_2026-11-01.json).
- [Resumo reproduzível das verificações](evidencias/SEGURANCA_2026-11-01.json).
