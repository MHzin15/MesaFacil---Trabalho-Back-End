# Reproduzir a validação de navegador

Pré-requisitos: instalação Python do README, PostgreSQL local de desenvolvimento,
Chrome instalado, Node e Playwright 1.62.1 para testes. Eles não são necessários
para executar o servidor Django. Instale o pacote de teste fora do projeto, por
exemplo `npm install --prefix .tmp/browser-tools playwright@1.62.1`.

Na raiz do projeto, prepare um banco **novo e exclusivo**:

```powershell
.\.venv\Scripts\python.exe scripts/browser_fixture.py
.\.venv\Scripts\python.exe scripts/browser_server.py
```

O primeiro comando só aceita servidor PostgreSQL local, cria um banco com prefixo
`mesafacil_browser_`, aplica migrations e popula os exemplos. Usuários e senhas são
exclusivos dessa rodada e ficam no arquivo ignorado `.tmp/browser-fixture.json`.
Não substitui a configuração do `.env` nem usa o banco de atendimento nos testes.
O segundo comando inicia o servidor de testes em `127.0.0.1:8765`, sem autoreload.

Em outro terminal:

```powershell
$env:PLAYWRIGHT_MODULE = (Resolve-Path .tmp/browser-tools/node_modules/playwright).Path
node scripts/check_flow.cjs
node scripts/check_regressions.cjs
node scripts/check_pwa.cjs
```

Execute nessa ordem. Para repetir a rodada desde o início, pare o servidor com
Ctrl+C, prepare uma fixture nova e reinicie. Os dados da rodada são preservados
no cluster de desenvolvimento para inspeção; não são dados de produção.

## O que os scripts verificam

- `check_flow`: login real por formulário, sessões de navegador independentes
  para cliente/cozinha/garçom/admin, carrinho com adicionais e observação, revisão,
  envio, todas as etapas até entrega, solicitação de conta, pagamento e mesa livre.
  Baixa o QR privado pelo admin e confere ausência de cache privado e overflow.
- `check_regressions`: disponibilidade por polling, quantidade/remoção, reajuste
  exigindo nova confirmação, resposta perdida após criação sem duplicar pedido,
  cancelamento antes do preparo e encerramento sem cobrança.
- `check_pwa`: perfil persistente exclusivo (instalação é bloqueada em navegação
  anônima), manifesto, critérios de instalabilidade, SW, offline, cardápio salvo,
  falha de POST sem conexão e ausência de respostas privadas no Cache API.

Os scripts não fazem chamadas externas de publicação. Resultados JSON, screenshots,
downloads e perfis ficam em `.tmp/`. O cenário funcional foi validado com viewports
390×844, 1280×800 e 1024×768, sem erros JavaScript ou rolagem horizontal.

Esta emulação não substitui a demonstração física em dois aparelhos exigida pelo
professor. Para essa demonstração, siga o roteiro em `ACEITE_FINAL.md` e use HTTPS.
