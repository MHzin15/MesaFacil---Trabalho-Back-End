# Registro de Prompt — Marco 3: Pedidos, Regras Críticas e Testes Automatizados

## Contexto do Projeto
Desenvolvimento do **MesaFácil**, PWA em Django + PostgreSQL para pedidos por QR Code em restaurantes.

## Objetivo deste Prompt
Implementar a suíte de testes automatizados com `pytest-django` cobrindo as regras de negócio críticas (RN01 a RN08) e estruturar/refinar o fluxo de pedidos e o painel da cozinha (RF13 a RF16).

## Prompt Utilizado
> "Atue como desenvolvedor backend especialista em Django, DRF e pytest-django.
> O Marco 1 e Marco 2 do MesaFácil estão implementados (models, serializers, views, seed_data e endpoints REST documentados).
> Sua tarefa é implementar os testes automatizados para blindar as regras de negócio críticas:
> - RN01: Transição válida de status (RECEBIDO -> EM_PREPARACAO -> PRONTO -> A_CAMINHO -> ENTREGUE). Bloquear saltos de etapa ou retrocesso.
> - RN02: Cancelamento permitido apenas enquanto o pedido estiver em RECEBIDO.
> - RN03: Auditoria em HistoricoStatusPedido a cada transição de status.
> - RN04 e RN05: Mesa só aceita pedidos com sessão aberta; mesa não pode ter 2 sessões abertas simultaneamente.
> - RN06 e RN07: Cálculo correto do valor do item ((preço + adicionais) * quantidade), testando caso de referência (Hambúrguer R$ 32,90 + Bacon R$ 5,00 + Queijo R$ 4,00 = R$ 41,90).
> - RN08: Produto indisponível não pode ser adicionado ao pedido.
> - RNF08: Preços unitários e de adicionais permanecem inalterados no pedido mesmo após modificação no cardápio.
> Garanta que os testes executem de forma isolada e rápida via pytest."

## Ajustes e Observações

Suíte em `restaurante/tests.py`, usando Django `TestCase` e DRF `APIClient`,
executável por pytest-django ou pelo runner do Django. As fixtures são criadas
pela própria suíte, sem depender de seed, PostgreSQL ou arquivo `.env`.

| Regra | Cenários cobertos |
|-------|------------------|
| RN01 e RN02 | Matriz independente com as 36 combinações entre os seis estados: cinco transições permitidas, saltos, retrocessos, repetição, estados finais e cancelamento. Rejeições retornam 400 e preservam status, horário e histórico. |
| RN03 | Histórico inicial anônimo/autenticado; autoria de cozinha e garçom no fluxo completo; status anterior/novo, horário com fuso e ordem dos registros; falha simulada na auditoria reverte criação ou alteração do pedido. |
| RN04 e RN05 | Sem sessão, sessão encerrada ou de outra mesa; mesa inativa; UUID inválido/inexistente; abertura duplicada pela API e diretamente no banco; consulta desatualizada simulando conflito na abertura; reabertura e associação apenas à sessão atual. |
| RN06 e RN07 | R$ 32,90 sem extras; R$ 41,90 com bacon e queijo; quantidades maiores e múltiplos itens; preços enviados pelo cliente ignorados; rejeição de quantidades inválidas, lista vazia e adicionais repetidos, inexistentes ou de outro produto. |
| RN08 | Produto indisponível retorna 400; um item inválido após itens válidos reverte pedido, itens, adicionais e histórico. Referências inexistentes retornam 404. |
| RNF08 | Pedido criado pela API mantém preços, adicionais e totais após reajuste; nova consulta preserva R$ 83,80, enquanto novo pedido usa R$ 132,00. |
| RF13–RF16 | Três colunas estáveis, inclusive vazias; ordem por antiguidade; mesa, horário, quantidades, adicionais e observações; próxima ação de preparo; mudanças refletidas nas consultas seguintes; disponibilidade refletida no cardápio e na criação de pedidos. |
| Permissões e limites | Cozinha/admin acessam o painel e disponibilidade; anônimos, usuário sem perfil e garçom são bloqueados; validação estrita de booleanos JSON e limite de 255 caracteres no item; número de consultas do painel não cresce com a quantidade de pedidos. |

### Correções implementadas

- Restrição condicional `uma_sessao_ativa_por_mesa` com migration incremental `0002_sessao_ativa_unica`; abertura em transação com bloqueio da mesa e tratamento do conflito como HTTP 400.
- Alteração de status e auditoria na mesma transação, com bloqueio do pedido.
- Serializers validam adicionais repetidos, limite da observação e disponibilidade com booleano JSON.
- Painel mantém as chaves `RECEBIDO`, `EM_PREPARACAO` e `PRONTO`, acrescentando `status_display` e `proximo_status` a cada cartão. Para `PRONTO`, `proximo_status` é `null`, pois o preparo foi concluído.
- Testes usam SQLite em memória antes de consultar `DATABASE_URL`, com chave exclusiva de testes quando não há configuração de ambiente.

### Validação

```bash
python -m pytest -q
python manage.py test restaurante
python manage.py check
```

Resultado: **39 testes aprovados**, com as 36 combinações de status verificadas
por subtestes, e `manage.py check` sem problemas. A suíte também passou com a
leitura de `.env` desativada e sem `SECRET_KEY`/`DATABASE_URL`; a verificação de
migrations não encontrou alterações pendentes de geração.

Os testes verificam todas as regras solicitadas; isso não representa uma medição
de 100% das linhas de código do projeto. Concorrência é protegida pela restrição
do banco e testada com conflito simulado; não foi executado teste concorrente em PostgreSQL.

Para aplicar a nova restrição no ambiente da aplicação, execute
`python manage.py migrate`. A suíte aplica as migrations automaticamente no banco temporário.
