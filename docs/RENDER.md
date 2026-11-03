# Publicação do MesaFácil no Render Free

**Decisão vigente do proprietário:** manter serviço web e PostgreSQL no plano
Free até nova autorização. O `render.yaml` da raiz é a configuração ativa.
Não inclui disco pago, mudança de plano ou `MEDIA_ROOT` dependente de volume.

## Configuração atual

- Web Python e PostgreSQL `plan: free`, região Virginia e PostgreSQL 18.
- Build: `bash scripts/render-build.sh`; start: `bash scripts/render-start.sh`.
- `DEBUG=False`, `SECRET_KEY` gerada pelo Render e conexão ao banco existente.
- Gunicorn com 1 worker/2 threads e redação de tokens nos logs.
- Health check em `/health/ready/`; `/health/live/` verifica apenas o processo.
- Fotos próprias no diretório local `media/`. As fotos padrão do cardápio ficam
  versionadas em `static/fotos-exemplo/` e não dependem de disco persistente.

As correções de segurança e de comandas funcionam no Free. O start não exige
backup agendado, ferramentas pg_dump, disco pago ou contratação de storage.
Preserve `SECRET_KEY`, `DATABASE_URL` e os UUIDs do cadastro na atualização.

## Publicar ou atualizar

Use o Blueprint da raiz e confira **Free** nos dois recursos antes de aplicar.
Mantenha o banco atual: não remova nem recrie o serviço de banco para atualizar
código. Informe uma senha inicial forte em `DJANGO_SUPERUSER_PASSWORD`; depois
que o administrador existe, essa variável não redefine sua senha.

O build coleta estáticos. O start aplica migrations para a frente, prepara o
cadastro inicial e inicia Gunicorn. O deploy automático continua ligado à main;
só faça push quando quiser publicar os commits correspondentes.

Se o serviço foi criado manualmente, use os mesmos comandos de build/start,
health check `/health/ready/`, ambos os planos Free e o PostgreSQL atual.
Não cadastre `PUBLIC_BASE_URL=localhost` no Render: o hostname HTTPS do serviço
é detectado automaticamente.

## Limitações conhecidas, aceitas por enquanto

O filesystem Free é efêmero, portanto fotos próprias enviadas pelo admin podem
se perder em reinícios/redeploys. As fotos padrão versionadas continuam
disponíveis. O banco Free tem limite de duração e o web pode hibernar; mantenha
cópias dos dados importantes. Essas condições do provedor não são removidas por
uma alteração de CSS ou de configuração Django. Nenhuma compra é necessária
para executar as correções já preparadas.

Para cópia e restauração manual, consulte [RECUPERACAO.md](RECUPERACAO.md).
O comando é opcional e executado em máquina de manutenção com acesso autorizado
ao banco e às fotos; não roda automaticamente no start do Free.

## Configuração futura paga, desativada

[deploy/render-paid.yaml.example](../deploy/render-paid.yaml.example) preserva
a proposta de banco durável e disco de mídia. É um **exemplo inativo**: a raiz
continua Free e nenhum procedimento deve aplicá-lo sem nova autorização.

Quando o proprietário avisar que contratou o plano, revisar disponibilidade e
preços, preservar o banco existente, copiar as fotos mantendo seus caminhos,
ativar backup externo e ensaiar recuperação antes de trocar a configuração.

## Logs e convites

O logger da aplicação redige tokens de convite e atendimento. Logs de borda e
retenção são administrados na conta do provedor; não exporte URLs privadas
para suporte público. Esta configuração não exige um serviço de logs pago.

## Referências

- [Render Free](https://render.com/docs/free)
- [Blueprints](https://render.com/docs/blueprint-spec)
- [Health checks](https://render.com/docs/health-checks)
