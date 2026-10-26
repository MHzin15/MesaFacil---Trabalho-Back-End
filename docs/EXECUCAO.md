# Execução do plano

Guia: [avaliação de 23/10/2026](AVALIACAO_E_PLANO_2026-10-23.md).
Cada etapa terá commit, push e evidência de validação antes da seguinte.

| Etapa | Situação | Evidência |
| --- | --- | --- |
| 1. Ambiente | Concluída | PostgreSQL 18.6: migrations, seed repetido, collectstatic e 45 testes aprovados; configuração rápida também aprovada. Compose preparado, execução Docker não disponível nesta máquina. |
| 2. Segurança e integridade | Concluída | 57 testes aprovados em PostgreSQL, incluindo 3 corridas com conexões reais; CSRF anônimo, QR privado, contexto de sessão, admin protegido e constraints. |
| 3. API, cliente e cozinha | Concluída | 62 testes em PostgreSQL; OpenAPI estrito sem erros/avisos; envio idempotente, disponibilidade no polling e totais padronizados. Validação de navegador na etapa 6. |
| 4. Garçom e pagamento | Concluída | 68 testes PostgreSQL; painel, conta de atendimento, três métodos, fluxo completo, repetição e rollback. Revisão de navegador na etapa 6. |
| 5. PWA | Implementada e validada em navegador | 72 testes PostgreSQL; Chrome sem erros de instalabilidade/manifesto, SW ativo, offline e cardápio salvo testados; cache privado ausente. Celular físico permanece na demonstração final. |
| 6. Aceitação | Validação técnica concluída; demonstração física pendente | 87 testes PostgreSQL, cinco corridas reais, fluxo visual completo, regressões e PWA. Pré-checagem e guia de ensaio acrescentados em 25/10. Ver ACEITE_FINAL.md para matriz e limites. |

A avaliação inicial é histórica. O estado atual de cada requisito está em [ACEITE_FINAL.md](ACEITE_FINAL.md).

## Continuação da etapa 6 — 25/10/2026

Repositório atualizado a partir de 129e005, sem alterações remotas adicionais.
Preparação do ensaio sem incluir opcionais: comando `verificar_demonstracao`
somente de leitura e [guia de operação](DEMONSTRACAO.md), incluindo pgAdmin,
sessões de navegador separadas, dois pedidos, pagamento, auditoria e offline.

A checagem real encontrou o cluster local parado e ausência dos três acessos da
equipe. O servidor exclusivo foi iniciado pelo script existente e os usuários
demonstrativos foram preparados explicitamente no ambiente local com DEBUG=True,
sem redefinir senhas existentes. Nada disso altera a política de instalação:
o seed normal continua sem criar usuários.

O modo `--celular` exige configuração HTTPS e troca de senhas conhecidas antes da
exposição. O comando não realiza publicação nem comprova acesso em outro aparelho.
A execução de Docker/Gunicorn e o aceite físico permanecem pendentes.

Validação repetida: **87 testes aprovados no PostgreSQL**, sem skips, incluindo
oito cenários da pré-checagem. Check, migrations, estáticos, OpenAPI estrito e
dependências aprovados. Os oito testes novos também passaram na configuração
rápida; a checagem local real passou após o preparo dos acessos demonstrativos.

## Uso local simplificado — 25/10/2026

A pedido do usuário, senhas de admin, cozinha e garçom cadastradas/redefinidas no
banco local e verificadas por formulário com CSRF. A relação com a credencial
real do PostgreSQL ficou somente em `.local/ACESSOS_LOCAIS.md`, ignorado pelo Git.

O guia DEMONSTRACAO.md foi simplificado para o primeiro uso no computador; o
roteiro detalhado foi preservado em ENSAIO_COMPLETO.md. A lista e o cadastro de
mesas no admin agora têm link para abrir o cardápio diretamente, sem leitor de QR.
Verificados: os três logins, os links autenticados, a página anônima da mesa,
a proteção do admin e o check do Django. Nenhuma regra de negócio foi alterada.

## Revisão do frontend no desktop — 25/10/2026

Defeito de clique reproduzido em 1920×1080: a foto extrapolava a área reservada e
interceptava o botão de adicionar. Corrigida a contenção da imagem e revisados
cardápio, personalização, carrinho, revisão, navegação da equipe e layout do salão.

87 testes PostgreSQL aprovados. Baterias de fluxo completo, regressões, desktop e
PWA aprovadas no Chrome, em banco isolado. A revisão inclui cinco resoluções,
recuperação de falhas, preços do carrinho restaurado e mensagens dentro do modal.
Reprodução e resultados em [REVISAO_FRONT_DESKTOP.md](REVISAO_FRONT_DESKTOP.md).
O ajuste manual já existente em DEMONSTRACAO.md foi preservado fora desta entrega.

## Acesso ao QR Code — 25/10/2026

Incluído botão Baixar QR Code diretamente na lista de mesas do admin, além do
cadastro individual. Validado botão no HTML autenticado, PNG válido e acesso
anônimo bloqueado. A geração continua na hora, com endereço público configurado.

O usuário esclareceu que procurava a ação na tela `/mesa/<uuid>/`. Adicionado
também botão no cabeçalho dessa página, abaixo da identificação da mesa, para
perfil ADMIN. Verificado no Chrome contra a URL local indicada: login com retorno
à mesa, botão visível e download PNG real. Anônimo e cozinha permanecem sem acesso.
