# Backup, restauração e atualização de comandas privadas

> Decisão vigente: manter Render Free até nova autorização. As metas de agenda
> e armazenamento durável abaixo são um plano futuro; não são pré-requisitos de
> startup e não implicam contratação automática. O comando de cópia manual segue
> disponível. A configuração paga está só em `deploy/render-paid.yaml.example`.

## Objetivos operacionais

Meta inicial de RPO: até uma hora de dados. Meta de RTO: até uma hora para
restaurar e conferir uma cópia. São metas a cumprir com agenda, retenção e ensaio
no ambiente real; o teste local não mede prazo de recuperação do Render.
O responsável pelo ambiente deve agendar o snapshot a cada hora, copiar a saída
para armazenamento protegido fora da instância, manter 48 cópias horárias e
30 diárias e revisar mensalmente uma restauração. Backups contêm dados de acesso
e devem ser criptografados e restritos a quem administra a operação.

## Criar cópia consistente

Instale as ferramentas PostgreSQL da mesma versão principal do servidor (18
nesta configuração). O comando usa o `DATABASE_URL` do ambiente selecionado,
sem mostrar senha nem incluí-la nos argumentos do processo. `MEDIA_ROOT` deve
apontar para as fotos reais da mesma instalação. Não execute este procedimento
em `core.test_settings`, que usa SQLite.

```powershell
python manage.py snapshot_restaurante criar C:/backup-seguro/mesa-20261102-2300 --pg-bin "C:/Program Files/PostgreSQL/18/bin"
```

No Linux, deixe `pg_dump` e `pg_restore` no PATH ou informe `--pg-bin`. Em um
container de aplicação que não tenha essas ferramentas, use uma máquina de
manutenção com PostgreSQL 18 e acesso ao banco e ao volume de mídia. O comando
não altera o banco de origem e recusa sobrescrever diretório de backup existente.

São gerados `database.dump`, `media.tar.gz` e `manifest.json`. Um snapshot
PostgreSQL exportado vincula o dump aos hashes e às contagens das tabelas de
domínio. As fotos são arquivadas com hashes SHA-256. Se uma foto cadastrada está
ausente, o comando falha e não escreve manifesto de sucesso. Preserve a pasta
com falha para diagnóstico e gere nova cópia depois de recuperar o arquivo.

Copie os três arquivos juntos para fora da instância. O disco persistente, por
si só, não é backup contra exclusão ou perda da conta do provedor. Não use o
repositório Git para guardar dumps; `/backups/` e `.tmp/` são ignorados.

## Restaurar primeiro em destino isolado

1. Crie um PostgreSQL vazio, separado da operação, sem executar `migrate` nele.
2. Selecione esse banco com `DATABASE_URL` em um ambiente de manutenção e
   configure `MEDIA_ROOT` para uma pasta nova e vazia. Preserve os valores do
   ambiente operacional e nunca imprima a URL com senha.
3. Use somente backups confiáveis da sua instalação. Hashes detectam corrupção,
   mas não autenticam um dump recebido de terceiros: restaurar SQL pode executar
   código. Não existe upload público de backups nesta aplicação.
4. Execute, substituindo o nome pelo banco vazio que você criou:

```powershell
python manage.py snapshot_restaurante restaurar C:/backup-seguro/mesa-20261102-2300 --confirmar-banco mesafacil_restauracao --pg-bin "C:/Program Files/PostgreSQL/18/bin"
```

O comando exige o nome exato, recusa banco que contenha tabelas e pasta de mídia
ocupada. Verifica os arquivos e caminhos antes de restaurar SQL. O `pg_restore`
usa uma única transação; ao final, os hashes de todos os registros de domínio e
fotos precisam coincidir com a origem. Falha depois da restauração mantém o
destino para diagnóstico; não troque a aplicação para um destino reprovado.

Depois da comparação, rode `manage.py check`, confira o login, os totais e as
fotos em uma instância de revisão. Para recuperar produção, suspenda novas
escritas durante a troca, preserve a instância anterior e a última cópia,
aplique eventuais migrations **para a frente** e só então altere o destino da
aplicação. Não restaure uma cópia antiga sobre novos pedidos.

## Atualização e rollback da aplicação

As migrations `0008` e `0009` consolidam comandas privadas. Voltar ao esquema
anterior de uma sessão por mesa pode perder as identidades de acesso e impedir
a restauração da restrição antiga. A `0009` bloqueia a reversão antes de executar
operações de downgrade. Use uma correção para a frente preservando o esquema.

Antes de atualizar, guarde snapshot e revisão do código, publique backend e
estáticos juntos e mantenha a compatibilidade de envios pendentes. Clientes
antigos com envio sem identificação devem atualizar a página; uma sessão já
identificada continua autorizada somente à própria comanda.

Se precisar recuperar uma versão anterior por incidente, ensaie o backup em
banco novo com a versão correspondente do código e transfira o atendimento
com uma janela de manutenção. Não use `migrate restaurante 0007` ou `--fake`
para forçar o retorno no banco operacional.

## Ensaio realizado em 02/11/2026

Dois bancos PostgreSQL locais descartáveis receberam dados artificiais, duas
comandas na mesma mesa, pagamento de R$ 20,00 e uma foto. O snapshot foi
restaurado em banco/pasta vazios: contagens, todos os valores de domínio e bytes
da foto conferiram. Uma segunda restauração foi recusada sem sobrescrever dados;
o downgrade foi recusado e as duas comandas foram preservadas.

Esse ensaio valida o comando no PostgreSQL 18 local. A agenda de cópias externas,
as permissões do provedor e o RTO de produção ainda precisam ser ativados e
medidos no ambiente publicado.
