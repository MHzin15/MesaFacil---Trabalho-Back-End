# Auditoria forense integral — MesaFácil

> Este relatório preserva os achados na versão auditada. A remediação posterior está em [CORRECOES_AUDITORIA_FORENSE_2026-11-02.md](CORRECOES_AUDITORIA_FORENSE_2026-11-02.md); não confundir o diagnóstico original com o estado após os patches.

**Data:** 02/11/2026 (America/Sao_Paulo)  
**Base auditada:** `main`, commit `21ddef48b83608482fbf73edf848e4e70ac6f10b` — `feat: implementa comandas privadas e compartilhamento entre clientes`  
**Escopo:** Django/DRF, fluxos de comandas e pedidos, gestão, interface, banco, dependências e configuração de deploy.

## Estado da versão auditada

A versão local de comandas privadas está integrada ao `main` local e foi usada como a base desta auditoria. O `main` local está um commit à frente de `origin/main`; não houve push nem deploy. Portanto, este parecer descreve o código no commit acima, não confirma qual versão está publicada.

A conferência de hashes encontrou os mesmos bytes nos 200 arquivos do manifesto inicial e no commit auditado. A alteração preexistente em `docs/DEMONSTRACAO.md` foi preservada e ficou fora do commit. A auditoria não alterou código, migrations ou dados de produção. Este documento é o único artefato novo em `docs/`; reproduções e evidências auxiliares estão em `.tmp/forense-2026-11-02/`.

## Conclusão executiva

O fluxo de várias comandas privadas por mesa continua compatível com autoatendimento sem presença do garçom: abrir a primeira comanda pelo pedido do cliente e encerrar uma família não deve fechar nem expor a comanda de outra. A prioridade de correção é tornar cada tentativa de pedido permanentemente vinculada à comanda privada que a iniciou. A solução recomendada preserva essa regra de produto; não exige que o garçom abra a sessão.

Foram confirmadas falhas de integridade em concorrência, uma falha de gestão acessível por caminho alternativo do Django Admin e respostas HTTP 500 em operações administrativas válidas. A configuração versionada do Render também seleciona planos Free, que não sustentam armazenamento durável de fotos e banco para uma operação contínua. Os itens abaixo separam defeitos reproduzidos de riscos dependentes da configuração realmente publicada.

## Achados priorizados

| ID | Prioridade | Problema e prova | Recomendação |
|---|---|---|---|
| MF-01 | **P1 — integridade de pedidos** | Uma chave de idempotência pode ser reutilizada em outra comanda se o contexto privado da sessão HTTP mudar entre envio e repetição. A API criou dois pedidos em comandas diferentes; o JavaScript real reproduziu a corrida entre abas. Reproduzido em SQLite e PostgreSQL descartáveis. | Vincular a tentativa a uma identidade imutável de rascunho/comanda e resolver retries no mesmo destino. Preserva o autoatendimento e as várias famílias por mesa. |
| MF-02 | **P2 — transação PostgreSQL** | Pedido simultâneo à mudança de um adicional para outro produto inverte a ordem dos locks e causa deadlock. Reproduzido com serviço e edição reais em PostgreSQL descartável. | Uniformizar a ordem de locks e revalidar o pai do adicional dentro da transação; considerar `no_key=True` somente após validar a semântica no PostgreSQL. |
| MF-03 | **P2 — autorização de gestão** | O Django Admin técnico permite ao gestor autenticado redefinir a senha de outro usuário sem a confirmação exigida pelo portal, suspender a si mesmo e rebaixar seu próprio perfil. Três cenários reproduzidos. | Aplicar as mesmas guardas em todos os caminhos ou reservar as rotas técnicas a um papel de suporte explícito. Ocultar links, sozinho, não fecha acesso direto à URL. |
| MF-04 | **P2 — operação do garçom** | Uma resposta atrasada da conta A pode atualizar o modal após a seleção mudar para B; as ações seguintes usam o ID B. Reproduzido no `garcom.js` real com DOM e respostas controladas. | Associar dados exibidos e ações a um snapshot de ID/geração; descartar respostas antigas e bloquear a ação quando a seleção mudou. |
| MF-05 | **P2 — alteração de preço** | Um formulário completo de produto aberto antes de um ajuste rápido pode salvar o preço antigo por cima do novo, mesmo quando o gestor só quis alterar a descrição. Reproduzido em banco descartável. | Usar versão otimista ou valor original também no formulário completo, ou deixar o preço em um único fluxo protegido. Preserva os snapshots de pedidos já feitos. |
| MF-06 | **P2 — erro em exclusão protegida** | `DELETE /api/mesas/<id>/` retorna 500 para gestor e superusuário quando há sessão histórica protegida (`ProtectedError`). A proteção de dados funciona, mas a API não converte a exceção em resposta de negócio. | Capturar a proteção como conflito `409` ou validação equivalente com mensagem útil. **Não** remover `PROTECT` nem apagar histórico. |
| MF-07 | **P1 antes de operar com dados reais, condicionado ao plano publicado** | `render.yaml` declara web e PostgreSQL Free. O web filesystem é efêmero; fotos enviadas podem sumir em reinício/redeploy. O PostgreSQL Free expira após 30 dias e é excluído depois da janela de 14 dias; o plano não tem backups lógicos. O plano e a data do serviço publicado não foram verificados. | Antes de usar como operação contínua, escolher banco durável, storage persistente de objetos para fotos e backup/restore ensaiado. Fixar RPO/RTO e testar uma restauração isolada. |
| MF-08 | **P3 — limite de upload** | O portal recusa foto acima de 5 MB, mas a API de produtos aceitou e gravou uma imagem válida de 7 MB com perfil ADMIN. Não foi demonstrada exaustão de disco. | Compartilhar limite de tamanho entre formulário, serializer e demais canais; não apagar arquivos antigos automaticamente. |
| MF-09 | **P3 — convite em logs** | O token de convite está no caminho da URL e o Gunicorn registra o caminho de requisição. A captura por terceiros não foi verificada; o risco depende de acesso e retenção dos logs. | Redigir o segmento secreto nos logs disponíveis a suporte/provedor, limitar acesso/retensão e validar que o convite continua utilizável por vários familiares. |
| MF-10 | **P3 — prontidão do serviço** | O health check configurado em `/` responde 200 sem consultar o banco, inclusive quando a conexão de banco falharia. Prova feita injetando erro de banco no teste local. | Separar liveness de readiness; readiness deve fazer consulta mínima com timeout e não induzir ciclos de reinício. |
| MF-11 | **P3 — acessibilidade** | O texto secundário do CSS tem contraste calculado de 4,14:1 e 4,48:1 em fundos usados, abaixo de 4,5:1 para texto normal. Não é certificação de todas as telas. | Escurecer o tom secundário ou ajustar os fundos e medir todos os estados informativos ativos. |
| MF-12 | **P3 — resiliência do cliente** | No ciclo do `cliente.js`, a leitura do catálogo precede as leituras de pedidos e conta; se o catálogo falhar, a atualização dessas informações também não ocorre naquele ciclo. Conclusão por inspeção, sem falha de rede injetada em navegador. | Tornar as leituras independentes; falha de catálogo deve bloquear apenas ações que dependem do catálogo válido. |
| MF-13 | **P3 — paginação estável** | A matriz de API emitiu `UnorderedObjectListWarning` para a lista de adicionais paginada sem ordenação padrão. Isso pode tornar páginas inconsistentes conforme os dados mudam. | Definir ordenação determinística, por exemplo chave primária, e manter filtros explícitos. |
| MF-14 | **P3 — rollback de migration** | A reversão da migration `0008` restaura a regra anterior de uma sessão ativa por mesa. Com várias comandas abertas, os dados podem não caber no esquema antigo; a reversão não foi executada. | Documentar rollback como migração corretiva/forward-fix e ensaiar cópia antes de qualquer downgrade. Não remover a feature de comandas privadas para satisfazer o esquema antigo. |
| MF-15 | **P3 — documentação** | Documentos chamados `ACEITE_FINAL.md` e avaliação de outubro ainda apresentam a antiga restrição de uma sessão por mesa como atual. São documentos datados, mas seus títulos podem induzir leitura como estado presente. | Marcar esses trechos como fotografia histórica e apontar `COMANDAS_PRIVADAS.md` como regra vigente. |

### Detalhes de integridade e concorrência

**MF-01 — vínculo da idempotência.** O primeiro pedido de um rascunho pode ser enviado com `sessao_id: null`. O serviço deriva a comanda do contexto HTTP atual e a unicidade da chave de envio fica limitada à comanda escolhida naquele momento. Se outra aba do mesmo navegador selecionar outra comanda antes do retry, a mesma intenção pode retornar outro pedido e outro destino. O estado estável no cliente normalmente troca o `draftId` e evita retry automático, mas a corrida entre leituras foi reproduzida. O pagamento da aplicação é simulado; não houve prova de cobrança bancária duplicada. O risco comprovado é duplicar ou encaminhar consumo para comanda errada.

A correção deve preservar o modelo multi-família: cada cliente inicia ou seleciona sua própria comanda sem depender do garçom. A intenção enviada precisa carregar a identidade privada esperada; o servidor valida o vínculo e deduplica por essa identidade mesmo que outra aba altere a seleção atual. Se não for possível recuperar o pedido original com segurança, responder conflito explícito em vez de associar silenciosamente a nova seleção.

**MF-02 — deadlock.** A criação de pedido bloqueia produtos e depois adicionais; a edição do adicional bloqueia o adicional e pode precisar do produto novo para validar a chave estrangeira. O teste concorrente espera a aquisição do primeiro lock e produz o interleaving; uma transação é abortada pelo PostgreSQL por deadlock. A operação deve ser repetida após correção de ordem e revalidação da relação do adicional, sem enfraquecer a consistência de preço e disponibilidade. A transação mantém atomicidade, então o teste não demonstrou corrupção; demonstrou falha da operação concorrente.

### Gestão e respostas de API

O portal próprio aplica confirmação de senha e evita que o gestor comum se suspenda ou rebaixe. As telas técnicas herdadas do Django Admin continuam acessíveis ao mesmo gestor e não reutilizam as mesmas regras. Isso não cria sessão anônima nem foi demonstrada escalada de papel; é uma divergência de autorização para ações sensíveis por caminho alternativo (OWASP A01/Broken Access Control; CWE-862).

O `DELETE` de mesa com histórico é uma operação negada pelo `PROTECT`, mas a exceção chega ao cliente como 500. A API deveria responder um conflito compreensível, sem mudar a retenção do histórico. A reprodução ocorreu duas vezes na matriz (gestor e superusuário), e a proteção do banco permaneceu intacta.

### Segurança: controles que passaram e resultados de scanners

- `pip-audit` examinou 30 distribuições instaladas e não encontrou CVEs conhecidos na consulta de 02/11/2026. `pip check` não encontrou dependências incompatíveis. Isso não elimina vulnerabilidade desconhecida nem garante que qualquer versão futura continue sem CVEs.
- `Bandit` reportou 11 itens: três B105 para senhas **demonstrativas** no comando `seed_data --demo-users`; a opção é bloqueada quando `DEBUG=False`. Um B104 é falso positivo: `0.0.0.0` é comparado como texto para classificar URL local, não é endereço de bind. Sete avisos B404/B603 são uso de subprocesso com lista de argumentos, sem `shell=True`, em ferramentas de desenvolvimento/validação; revisão manual não indicou execução de entrada shell arbitrária.
- Pesquisa do histórico Git cobriu 476 blobs alcançáveis e os 200 arquivos do manifesto para padrões de chaves PEM, AWS, GitHub e token OpenAI; não encontrou correspondência para essas quatro famílias. Arquivos locais ignorados e credenciais de ambientes reais não foram abertos. Isto não certifica ausência de senhas arbitrárias.
- Testes não demonstraram SQL injection, XSS refletido/armazenado nos campos examinados, bypass de CSRF, acesso horizontal a comanda alheia ou CSV formula injection no relatório atual. O resultado é limitado ao código e casos verificados, não certificação de ausência.
- A matriz de permissões executou 399 combinações de método/endpoint/perfil; 126 leituras adicionais cobriram 18 rotas por sete perfis. Foram revalidados CSRF em escrita anônima, checagem de preços no servidor, acesso da comanda por capacidade privada e bloqueio de rotas de equipe para usuário inativo.
- `manage.py check` não apontou problemas; `makemigrations --check --dry-run` informou que não há migration pendente; validação estrita de OpenAPI terminou sem avisos. Com configuração sintética de produção, `check --deploy --tag security` apontou somente HSTS `includeSubDomains` e `preload` não definidos. São decisões de domínio/provedor a avaliar, não vulnerabilidades provadas; não se deve ativar preload sem controlar todos os subdomínios.

## Performance e manutenção

No microbenchmark local, com dados artificiais de 10, 50 e 100 mesas, as consultas por resposta permaneceram em 5 para mapa de mesas, 6 para cozinha e 8 para garçom. Isso não mostrou crescimento N+1 nesse cenário. Com 100 mesas e 600 pedidos artificiais, a mediana da API de cozinha foi 259 ms e a resposta teve cerca de 357 KB; o endpoint do garçom teve mediana 85 ms e cerca de 107 KB. São medições de processo local, três requisições por tamanho, sem carga real, rede, p95, CPU ou memória; não representam capacidade de produção.

O achado prático é o crescimento do corpo de respostas com o número de pedidos. Antes de alterar arquitetura, medir com dados representativos e observar percentis/uso de recursos. Se o volume real exigir, considerar filtros temporais para histórico e paginação compatível com filas ativas. Não há evidência que justifique microserviços, filas distribuídas ou índices novos agora. Os artefatos EXPLAIN foram gerados, mas não bastam para escolher índices em produção.

O aviso de ordenação de adicionais é um ajuste barato de determinismo. O fallback visual para fotos indisponíveis evita espaço quebrado, mas não fornece persistência do arquivo.

## Verificações executadas

- Suíte principal: **171 testes e 158 subtestes aprovados** em PostgreSQL 18.6 descartável local; nenhum banco publicado foi consultado.
- Sondagens PostgreSQL: 5 casos, **4 aprovados e 1 falhou por detectar o 500 esperado como achado**. Entre os aprovados estão a reprodução de deadlock e a divergência do limite de upload. Microbenchmark e matriz foram registrados; a matriz falhou apenas nas duas exclusões protegidas de mesa.
- Reproduções do domínio: retry de pedido com troca de comanda e sobrescrita de preço por formulário antigo foram confirmados em SQLite e PostgreSQL descartáveis.
- Testes específicos de segurança: três cenários de caminho alternativo do Django Admin, matriz de 126 leituras e upload acima de 5 MB foram reproduzidos com dados sintéticos.
- A tentativa de repetir o teste de deadlock depois da conclusão foi impedida pelas permissões do sandbox para conectar ao processo/porta local. A evidência positiva é a execução anterior registrada em `pytest-sondagens.xml` e `pytest-sondagens.log`; o teste está em `test_concorrencia_forense.py`.
- O PostgreSQL descartável desta auditoria foi encerrado ao final. Nenhum teste ou script foi executado contra produção.

## Plano recomendado

1. Corrigir e testar a identidade imutável da tentativa de pedido e o retry entre abas, preservando autoatendimento e comandas independentes.
2. Corrigir a ordem dos locks do pedido e da edição de adicional; repetir o teste concorrente PostgreSQL sem deadlock.
3. Fechar a divergência de guardas entre portal e Django Admin; tornar o modal do garçom e as ações vinculados ao mesmo ID de comanda.
4. Evitar sobrescrita de preço por formulário obsoleto e devolver conflito compreensível ao excluir mesa protegida.
5. Antes de operação continuada, confirmar os planos reais do Render e implantar banco, fotos e backup/restauração duráveis.
6. Unificar o limite de upload, redigir tokens dos convites em logs e tornar o readiness dependente de banco.
7. Melhorar contraste, ordenar adicionais, desacoplar polling do cardápio e atualizar documentos históricos.

## Referências e evidências

- A configuração versionada do Render é `render.yaml`; as limitações dos planos Free (filesystem efêmero, expiração de PostgreSQL em 30 dias e janela de 14 dias) estão na documentação oficial [Render Free](https://render.com/docs/free). As opções/limites de armazenamento estão em [Render Persistent Disks](https://render.com/docs/disks) e [Render Postgres backups](https://render.com/docs/postgresql-backups).
- A análise de validação, fluxo sequencial e locks de regra de negócio foi alinhada ao [OWASP ASVS 5.0, capítulo V2](https://github.com/OWASP/ASVS/blob/master/5.0/en/0x11-V2-Validation-and-Business-Logic.md).
- Evidências locais: `.tmp/forense-2026-11-02/evidencias/`; pareceres de domínio, segurança e frontend estão em `.tmp/forense-2026-11-02/{dados,seguranca,frontend}/relatorio.md`.

**Limite deste parecer:** não houve pentest da aplicação publicada, teste de recuperação de backup, inspeção das configurações reais do provedor, teste em celulares/redes reais ou auditoria fiscal. Os achados condicionais são apresentados como riscos e não como incidentes observados.
