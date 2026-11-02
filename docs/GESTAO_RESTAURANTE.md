# Gestão do restaurante — repaginação do admin

## Objetivo

A entrada `/admin/` agora oferece uma área de gestão própria, com linguagem de
restaurante, navegação por tarefas e a identidade visual do MesaFácil. O gestor
não precisa conhecer modelos, permissões técnicas ou os formulários do Django
Admin para realizar a rotina principal.

O login continua em `/entrar/`. Pessoas com função ADMIN chegam à nova gestão;
garçons e cozinha continuam em seus respectivos painéis. A administração
técnica permanece em `/admin/avancado/`, com atalho exibido apenas para o
responsável técnico que possui superusuário. URLs antigas de edição do Django
Admin continuam compatíveis com os acessos já existentes.

## Requisitos implementados

| Área | O que o gestor consegue fazer | Critério de aceite |
| --- | --- | --- |
| Visão geral | Ver recebimentos e pedidos do dia, ocupação atual, cancelamentos, contas solicitadas e produtos pausados | Indicadores vêm dos registros do banco; dados vazios têm explicação e próximo passo |
| Equipe | Cadastrar nome, usuário, e-mail opcional, senha inicial e função | Senhas fortes, usuário único e funções Gestor, Garçom ou Cozinha |
| Acessos | Editar função, liberar ou suspender login | Suspensão preserva registros anteriores; campos técnicos não são expostos |
| Senha esquecida | Definir uma nova senha para uma pessoa da equipe | Confirmação da senha do gestor, validação da senha nova e encerramento das sessões antigas do funcionário |
| Próprio acesso | Redefinir a própria senha | Sessão atual preservada; o gestor não pode se suspender ou retirar sua própria função pelo portal |
| Mesas | Cadastrar, editar número e ativar/desativar | Mesa ocupada não pode ser desativada; o UUID e o QR Code são preservados |
| Atendimento | Abrir sessão de uma mesa e acessar o salão | Reutiliza as regras transacionais existentes; abertura duplicada é rejeitada |
| QR Codes | Baixar PNG e abrir o cardápio da mesa | Download restrito à gestão; sem UUID exposto como campo de edição |
| Cardápio | Cadastrar/editar produto, foto, descrição, categoria, preço e disponibilidade | Validação de preço não negativo, imagem válida e limite de 5 MB |
| Preço rápido | Alterar preço diretamente a partir do produto | Aceita vírgula decimal; rejeita sobrescrita quando o preço mudou desde que o formulário foi aberto |
| Disponibilidade | Pausar e liberar produtos | Afeta novos pedidos, sem excluir o produto ou seu histórico |
| Categorias | Cadastrar, renomear e ordenar categorias | A ordem menor aparece primeiro no cardápio |
| Adicionais | Cadastrar e editar opções de personalização por produto | Preço e vínculo validados; snapshots de pedidos permanecem preservados |
| Pedidos | Buscar por período e etapa, abrir detalhe e consultar a linha do tempo | Itens, observações, adicionais, preços históricos e responsável por transição visíveis |
| Cancelamento | Confirmar o cancelamento de pedido recebido | Somente antes do preparo, conforme a regra já existente; confirmação por POST |
| Recebimentos | Consultar total, número de contas, valor médio e distribuição por meio de pagamento | Somente contas pagas no período, com datas no fuso do restaurante |
| Exportação | Baixar as contas do período em CSV | Mesmas restrições de acesso e período; até 10 mil contas por arquivo, sem truncamento silencioso |
| Histórico de alterações | Consultar autor, horário, objeto e descrição da alteração | Cadastros, preços, disponibilidade e redefinições de senha registrados; nenhuma senha é gravada no log |
| Usabilidade | Usar filtros, paginação, mensagens de resultado e estados vazios | Nenhuma ação depende de códigos internos, conhecimento dos modelos ou permissões técnicas |
| Celular | Abrir menu expansível e gerenciar equipe em cartões | Ações de acesso e senha ficam visíveis sem rolagem horizontal na lista de equipe |

## Regras e segurança

- Todos os endpoints da gestão exigem usuário autenticado, ativo e com perfil
  ADMIN. Esconder botões não é a única verificação: o servidor valida cada rota.
- Escritas exigem CSRF. Operações de disponibilidade e abertura de mesa aceitam
  apenas POST; cancelamento tem confirmação explícita.
- Funcionários comuns não podem editar contas de superusuário pelo portal. O
  cadastro também ignora campos forjados de superusuário, grupos e permissões.
- Atualizações são transacionais e bloqueiam os registros editados no PostgreSQL.
  O histórico é salvo na mesma transação. As regras de pedido e mesa usam os
  serviços existentes, evitando caminhos alternativos para fechamento ou cobrança.
- Produtos e funcionários são pausados/suspensos, preservando o histórico. Não
  foram adicionados botões de exclusão destrutiva na gestão.
- As páginas, relatórios e CSV são `no-store`; não entram no cache público do PWA.
- Os valores em recebimentos representam os **pagamentos simulados** do sistema.
  Não são saldo bancário, lucro, conciliação financeira ou escrituração fiscal.

## Requisitos comuns de ERP levantados para os próximos módulos

A pesquisa de referência identificou cadastro de colaboradores, indicadores,
cardápio, frente de caixa, estoque, compras, financeiro e ficha técnica como
áreas usuais. A [visão do TOTVS Food Service](https://www.totvs.com/varejo/food-service/)
descreve esses módulos; a [ficha técnica do produto](https://produtos.totvs.com/ficha-tecnica/tudo-sobre-o-totvs-food-service/)
detalha a baixa de insumos e o controle de estoque mínimo.

A tabela abaixo transforma essa referência em propostas para este restaurante.
Esses módulos **não estão implementados** e não aparecem como botões sem função
no painel entregue.

| Prioridade proposta | Requisito | Dados e decisões necessários |
| --- | --- | --- |
| Alta | Estoque de ingredientes com alerta de mínimo | Unidades de medida, locais de estoque, saldo inicial, perdas, ajustes e permissões |
| Alta | Ficha técnica e custo por prato | Receita de cada produto, rendimento, conversão de unidades e custo dos insumos |
| Alta | Compras e fornecedores | Cadastro de fornecedor, entradas, preços de compra e vínculo com ingredientes |
| Alta | Fechamento de caixa por turno | Operadores, fundo de caixa, sangrias, reforços, diferenças e aprovação de ajustes |
| Alta | Armazenamento persistente de fotos | Escolher e configurar armazenamento permanente para uploads; o disco do Render Free é temporário |
| Média | Contas a pagar e fluxo de caixa | Despesas, vencimentos, centros de custo e fontes de recebimentos reais |
| Média | Conciliação e integração de pagamentos | Provedor, estados de autorização/estorno, webhooks, idempotência e acesso às contas do estabelecimento |
| Média | Indicadores de produtos e margem | Definir venda realizada, tratamento de cancelamentos, custo histórico e período de competência |
| Média | Impressão de comandas | Impressoras, setores de produção e regras de reimpressão |
| Conforme operação | Reservas, horários e capacidade de mesas | Capacidade, tolerância, bloqueios de agenda e políticas de cancelamento |
| Conforme operação | Delivery e retirada | Áreas/taxas, entregadores, integrações e estados de acompanhamento |
| Conforme operação | Documentos fiscais | Regime tributário, localização, credenciais e integração com serviço fiscal autorizado |

## Arquitetura e implantação

- `restaurante/gestao/`: formulários, views e URLs da gestão.
- `templates/gestao/`: telas próprias; reutilizam o cabeçalho e componentes do site.
- `static/css/gestao.css`: layout responsivo, sem aplicar regras de estilo do Django Admin.
- `static/js/gestao.js`: apenas fallback visual para fotos que não puderem ser carregadas.
- Auditoria usa `django.contrib.admin.models.LogEntry`, já existente no banco.
  Não há nova migração de domínio nem novas dependências.
- O novo código não transfere ou apaga dados existentes. A alteração principal
  de navegação é a entrada `/admin/`.

Após atualizar o código, execute `python manage.py collectstatic --noinput`.
O build do Render já executa esse passo. Não foi realizado push ou deploy nesta
etapa; a alteração pré-existente em `docs/DEMONSTRACAO.md` foi preservada.

As fotos ilustrativas são estáticas e continuam disponíveis. Fotos próprias
enviadas ao disco temporário do Render Free ainda precisam de armazenamento
persistente para sobreviver a uma reinstância; esse limite não foi ocultado por
um formulário novo.

## Validação

As regressões de gestão cobrem autorização, CSRF, criação de equipe, rejeição de
senhas fracas e papéis forjados, suspensão, troca de função, bloqueio de edição
de superusuários, recuperação de senha, sessão após troca da própria senha,
mesa ocupada, abertura duplicada, preços históricos, edição concorrente de
preço, vírgula decimal, novos produtos/adicionais, upload inválido, cancelamento,
relatórios e exportação.

Comandos para repetir:

```powershell
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest --ds=core.settings -q
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Também foram conferidos no navegador: painel, cadastro de funcionário, catálogo,
menu móvel e lista de equipe. Os testes de formulário executam as gravações em
bancos de testes; a prévia utiliza dados locais isolados.

Resultados registrados nesta entrega:

- Suíte completa no PostgreSQL: **139 testes aprovados e 155 subtestes aprovados**.
- Suíte completa no SQLite: **133 aprovados**, seis ignorados por exigirem PostgreSQL,
  além de 155 subtestes aprovados.
- Após o último ajuste do registro de preços: **20 testes da gestão e 36 subtestes
  aprovados no PostgreSQL**, com warnings tratados como erros.
- Bandit no novo módulo de gestão: nenhum alerta e nenhum erro de leitura.
- Checks do Django, detecção de migrações faltantes, geração estrita do OpenAPI,
  sintaxe do JavaScript, coleta de estáticos e `git diff --check` concluídos.
