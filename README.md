# MesaFácil

Pedidos por QR Code em um restaurante, com Python, Django, DRF e PostgreSQL.
O MVP inclui cardápio, carrinho, pedidos, cozinha, garçom, conta, pagamento
simulado e PWA. A implementação seguiu [o plano](docs/AVALIACAO_E_PLANO_2026-10-23.md);
consulte [o aceite final](docs/ACEITE_FINAL.md) para evidências e demonstrações ainda pendentes.
Acompanhe as entregas em [docs/EXECUCAO.md](docs/EXECUCAO.md).
Para ligar o projeto, conectar o pgAdmin e ensaiar cada papel pelas telas, siga
[o guia de demonstração](docs/DEMONSTRACAO.md).
Para publicar uma versão de testes com deploy automático a cada push,
siga [o guia do Render Free](docs/RENDER.md).
Consulte também a [auditoria de requisitos, domínio e decisões técnicas de 28/10](docs/RELATORIO_TECNICO_E_PRODUTO_2026-10-28.md)
para o parecer atual e as pendências de aceite.

## Stack

Python 3.12+ (validado em 3.13), Django 6.1.2, DRF, PostgreSQL 18 e psycopg 3.
Dependências diretas estão fixadas em requirements.txt, com versões estáveis
consultadas no PyPI em 23/10/2026. HTML/CSS, Bootstrap 5.3.8 local e Fetch no frontend.

Pacotes extras: drf-spectacular documenta a API; django-filter filtra consultas;
django-environ lê o ambiente; qrcode/Pillow geram QR e imagens; WhiteNoise serve
estáticos; pytest/pytest-django executam testes. CORS tem configuração explícita
para integração futura. Gunicorn é instalado apenas em Linux/container.

## Instalação local — Windows/PowerShell

```powershell
git clone https://github.com/MHzin15/MesaFacil---Trabalho-Back-End.git
cd MesaFacil---Trabalho-Back-End
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(50)); print(secrets.token_hex(24))"
```

Coloque a primeira saída em SECRET_KEY. Use a segunda como POSTGRES_PASSWORD e
na senha de DATABASE_URL. Não publique .env. Em instalações existentes, preserve
os segredos: acrescente DATABASE_URL sem substituir o arquivo inteiro.

DATABASE_URL deve apontar para um banco e usuário próprios, por exemplo:
`postgresql://mesafacil:SENHA@127.0.0.1:5432/mesafacil`.
Crie o usuário e o banco na sua instalação PostgreSQL. Para testar, o usuário
precisa de CREATEDB em um servidor exclusivo de desenvolvimento.

Alternativamente, com PostgreSQL instalado no Windows, o projeto pode manter um
cluster próprio em .local/postgres, sem alterar seus outros bancos:

```powershell
.\.venv\Scripts\python.exe scripts/dev_postgres.py start
```

O script lê DATABASE_URL, inicia na porta configurada, cria o banco se necessário
e usa os binários de `C:\Program Files\PostgreSQL\18\bin` (ou --bin CAMINHO).
Escolha uma porta livre na URL, como 55432, para evitar conflito com outro servidor.
Esse cluster exclusivo de desenvolvimento usa o usuário do projeto também para
administrar os bancos de testes. Para parar: substitua start por stop.
Não armazene bancos de produção em diretórios sincronizados por OneDrive.

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_data --demo-images
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

O seed cria 10 mesas, 6 categorias e 15 produtos com adicionais. É repetível:
não redefine preços ou senhas existentes. --demo-images cria ilustrações locais
para produtos sem foto; substitua pelas fotos do restaurante no admin.
Por padrão nenhum usuário é criado. Somente em demonstração local, execute
`python manage.py seed_data --demo-users` para criar admin/admin123,
cozinha/cozinha123 e garcom/garcom123. Não use essas credenciais em publicação.
Superusuários novos recebem Perfil ADMIN. Após atualizar uma instalação existente,
execute `python manage.py sync_roles`. Administradores comuns usam perfil ADMIN,
sem privilégios de superusuário; cadastre usuários e perfis no admin.

## Docker Compose

Configure .env a partir do exemplo, com uma senha hexadecimal, e execute:

```powershell
docker compose up --build -d
docker compose exec web python manage.py seed_data --demo-images
docker compose exec web python manage.py createsuperuser
```

Compose executa Django com Gunicorn e PostgreSQL em serviços separados, aplica
migrations e collectstatic ao iniciar. Não cria usuários automaticamente.
Para executar Django fora do container, suba apenas o banco com
`docker compose up -d db` e use DATABASE_URL local. Senhas com caracteres reservados
precisam de codificação na URL; a senha hexadecimal sugerida evita essa diferença.

## Testes e validação

```powershell
# Integração: usa PostgreSQL; primeiro atualize os estáticos de produção.
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py test
# Equivalente com pytest:
.\.venv\Scripts\python.exe -m pytest --ds=core.settings -q
# Rápidos: SQLite em memória selecionado explicitamente no pytest.ini.
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
```

A aplicação normal rejeita SQLite. core.test_settings é apenas para testes rápidos,
nunca para runserver ou entrega. Validação de 25/10: 87 testes aprovados em PostgreSQL
18.6, incluindo cinco corridas reais; schema estrito e dependências sem problemas.
Use `python scripts/validate.py` para repetir os checks técnicos. Docker ainda requer validação
em uma máquina com Docker disponível.

Na revisão de navegação de 29/10, o PostgreSQL executou 98 testes: 97 aprovados e
uma falha de senha no bootstrap do Render que já existia antes das mudanças.
Os cenários de interface passaram. Veja [o registro de UI/UX](docs/UX_NAVEGACAO_2026-10-29.md).

Antes do ensaio, execute `python manage.py verificar_demonstracao`. A pré-checagem
somente lê o banco e a configuração: aponta migrations, dados, fotos e acessos
que faltam. No ambiente HTTPS dos dois aparelhos, use `--celular` para conferir
também endereço, origens, cookies e troca de senhas demonstrativas. Esse comando
não testa a rede nem substitui o fluxo presencial.

## Acesso e API

- Entrada: http://localhost:8000/
- Login da equipe: /entrar/; administração: /admin/.
- Cliente: /mesa/<UUID>/; cozinha: /cozinha/.
- Cliente tem telas de carrinho, pedidos e conta em /mesa/<UUID>/carrinho/,
  /mesa/<UUID>/pedidos/ e /mesa/<UUID>/conta/, com navegação própria.
- API: /api/; Swagger: /api/docs/; ReDoc: /api/redoc/.
- Contratos e pendências detalhados no plano e no registro de execução.

A geração atual de QR é POST /api/mesas/<id>/gerar_qrcode/.
A API usa sessões Django e exige CSRF em toda escrita, inclusive anônima.
A identificação GET /api/mesa/<UUID>/ estabelece o contexto e cookie CSRF;
criar pedido exige também sessao_id. Envie X-CSRFToken nas escritas Fetch.
QR Code é baixado por GET /api/mesas/<id>/qr-code/ com perfil ADMIN.
O garçom acessa /garcom/: mapa de mesas, entregas, contas e pagamento simulado.
A cozinha também pode cancelar um pedido recebido, antes de iniciar o preparo.
O PWA tem manifesto, instalação e página offline; consulte [docs/PWA.md](docs/PWA.md).

No celular, localhost refere-se ao próprio celular. Configure PUBLIC_BASE_URL,
ALLOWED_HOSTS e CSRF_TRUSTED_ORIGINS para um endereço alcançável e HTTPS.
Com DEBUG=False os cookies exigem HTTPS. O service worker também exige
HTTPS ou localhost. Não exponha runserver como servidor de produção.

## Organização e colaboração

- core/: configurações e URLs; restaurante/: domínio, API, admin e testes.
- templates/ e static/: interface e consumo de API com Fetch.
- docs/prompts/: prompts adaptados por etapa, com critérios e correções.
- Membro 1: backend, banco, integridade e API.
- Membro 2: interface, PWA, testes de uso e demonstração em dois aparelhos.

Cada etapa deve terminar com testes, commit, push e uma demonstração curta.
Datas e nomes da dupla devem ser preenchidos pelos integrantes conforme o professor.
O escopo obrigatório é um restaurante; sem gateway real, multi-tenant, nota fiscal
ou impressão de comandas. Opcionais só após o MVP validado.

## Evidências e demonstração

[ACEITE_FINAL.md](docs/ACEITE_FINAL.md) mapeia todos os requisitos do enunciado às
evidências. [VALIDACAO_NAVEGADOR.md](docs/VALIDACAO_NAVEGADOR.md) descreve testes
reproduzíveis em banco isolado e sessões de navegador separadas, incluindo perda
de resposta sem duplicar pedido. A demonstração em dois aparelhos físicos e a
apresentação pela dupla continuam necessárias para o aceite do semestre.
