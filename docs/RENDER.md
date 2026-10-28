# Testar o MesaFácil no Render Free

O `render.yaml` da raiz cria um Web Service Python e um PostgreSQL, ambos no
plano **Free**, na mesma região. A branch `main` é publicada automaticamente a
cada push. Python 3.13 é selecionado pelo arquivo `.python-version`.

## Primeira publicação

1. Envie os arquivos desta configuração para o GitHub. O Render precisa receber
   `render.yaml`, `.python-version`, `.gitattributes`, os scripts e as alterações
   Python; arquivos somente nesta máquina não chegam ao Render.
2. Entre em [dashboard.render.com](https://dashboard.render.com), conecte sua
   conta GitHub e permita acesso ao repositório
   `MHzin15/MesaFacil---Trabalho-Back-End`.
3. Selecione **New → Blueprint**, escolha esse repositório e a branch `main`.
   Use `render.yaml` como caminho do Blueprint.
4. Confira que `mesafacil` e `mesafacil-db` aparecem como **Free**.
5. Preencha `DJANGO_SUPERUSER_PASSWORD` com uma senha longa e única para o
   administrador `admin`. Guarde essa senha; ela não deve ir para o GitHub.
   Não use as senhas de demonstração local.
6. Aplique o Blueprint e acompanhe os logs até o serviço ficar **Live**.
7. Abra a URL `https://...onrender.com` mostrada pelo Render. O subdomínio pode
   receber um sufixo; o projeto detecta o endereço real automaticamente.

O Render gera `SECRET_KEY`, conecta `DATABASE_URL` ao novo banco e desativa
`DEBUG`. Não copie o `.env` local nem a URL do PostgreSQL da faculdade.

O build instala dependências e coleta os estáticos. Ao iniciar, o serviço aplica
as migrations, cria o primeiro administrador, prepara mesas/cardápio/imagens e
sincroniza permissões. Então inicia Gunicorn na porta fornecida pelo Render.
Isso funciona sem shell e sem pre-deploy command, recursos ausentes no Free.

## Acessar e atualizar

- Administrador: `/admin/` ou `/entrar/`, usuário `admin` e a senha do Blueprint.
- Mesas e QR Codes: abra **Mesas** no admin. O QR usa o endereço HTTPS publicado.
- Cozinha e garçom: crie usuários no admin e associe os perfis `COZINHA` e `GARCOM`.
  Não são criados usuários públicos com senhas conhecidas.
- A API fica em `/api/docs/`; o PWA pode ser instalado pelo navegador no celular.

Depois de alterar e testar o código, faça commit e push para a `main`. O Render
executará outro deploy automaticamente. Alterações sem commit ou sem push não
aparecem no site. No painel, **Manual Deploy → Deploy latest commit** permite
repetir uma publicação; **Logs** mostra falhas de instalação ou de inicialização.

Reiniciar não redefine senhas, preços, pedidos nem identificadores das mesas.
Para trocar a senha do administrador, use o admin. Depois que o usuário existe,
alterar `DJANGO_SUPERUSER_PASSWORD` no painel não redefine sua senha no banco.

## Limites que afetam este projeto

- O serviço dorme após 15 minutos sem tráfego. O primeiro acesso depois disso
  pode demorar cerca de um minuto.
- O PostgreSQL Free expira em **30 dias**. Ele não oferece backups automáticos;
  não mantenha dados importantes apenas nesse banco de teste. O plano prevê
  expiração, não uma migração automática para um banco pago.
- Arquivos enviados ao servidor somem em redeploys, reinícios e hibernação.
  As ilustrações demonstrativas são recriadas ao iniciar. **Fotos próprias
  enviadas pelo admin precisam de armazenamento externo** para persistir; esta
  configuração não inclui esse serviço. QR Codes baixados são gerados na hora.
- O workspace tem limites mensais de horas, tráfego e builds. Mantenha os dois
  recursos como Free e confira o uso/faturamento no painel.

Para usar PostgreSQL externo (por exemplo, Neon), substitua o `fromDatabase` de
`DATABASE_URL` por `sync: false`, remova a seção `databases` antes de criar o
Blueprint e informe a URL com SSL fornecida pelo provedor. O PostgreSQL de teste
local e seus dados não são enviados para o Render.

## Se criar o serviço manualmente

Crie primeiro um PostgreSQL **Free**. Depois crie um **Web Service**, escolha
explicitamente **Python 3**, branch `main`, plano **Free**, e configure:

| Campo | Valor |
| --- | --- |
| Build Command | `bash scripts/render-build.sh` |
| Start Command | `bash scripts/render-start.sh` |
| Health Check Path | `/` |
| Auto-Deploy | A cada commit |
| `DEBUG` | `False` |
| `SECRET_KEY` | Gere um valor aleatório no painel |
| `DATABASE_URL` | Internal Database URL do PostgreSQL na mesma região |
| `DJANGO_SUPERUSER_USERNAME` | `admin` |
| `DJANGO_SUPERUSER_PASSWORD` | Senha longa e única escolhida por você |

Escolha Python mesmo com um `Dockerfile` no repositório. A configuração Compose
local não é usada por esse deploy. Não cadastre `PUBLIC_BASE_URL=localhost`:
o host, a origem CSRF e a URL dos QR Codes já são detectados no Render.

## Referências

- [Django no Render](https://render.com/docs/deploy-django)
- [Blueprints](https://render.com/docs/blueprint-spec)
- [Variáveis fornecidas pelo Render](https://render.com/docs/environment-variables)
- [Python no Render](https://render.com/docs/python-version)
- [Limites do plano Free](https://render.com/docs/free)
