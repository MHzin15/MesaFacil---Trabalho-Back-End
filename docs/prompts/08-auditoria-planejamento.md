# Prompt 08 — Atualização, auditoria e planejamento do MVP

Data: 23/10/2026.

## Contexto

MesaFácil em Python/Django para um restaurante. O usuário pediu `git pull`,
avaliação do estado atual e um plano rigoroso conforme todos os requisitos do
trabalho, deixando a implementação para uma próxima etapa.

## Prompt adaptado

Atualize o repositório preservando trabalho local não commitado. Avalie a versão
atual contra RF01–RF25, RNF01–RNF13 e RN01–RN10, distinguindo interface, backend,
documentação e evidência de funcionamento. Execute a suíte existente e verificações
necessárias em ambiente isolado. Não implemente correções nesta etapa.

Elabore diagnóstico rastreável e plano incremental com critérios de aceite,
priorizando segurança, integridade transacional e PostgreSQL antes de completar
garçom, fechamento e PWA. Mantenha Django/DRF, PostgreSQL/psycopg 3, QR/Pillow,
configuração por ambiente, Bootstrap 5, Fetch e polling. Não acrescente multi-tenant,
gateway real, nota fiscal, impressão de comandas ou opcionais ao escopo obrigatório.

## Critérios de aceite desta etapa

- Pull realizado ou impedimento explicado, sem perda de arquivos locais.
- Commit e versão avaliados identificados; suíte e limites de validação registrados.
- Matriz completa dos requisitos e das regras, sem tratar endpoint como tela pronta.
- Problemas confirmados separados de riscos e validações ainda não realizadas.
- Plano salvo com etapas, dependências e critérios verificáveis de conclusão.
- Nenhuma funcionalidade implementada e nenhum push efetuado.

## Resultado

Pull concluído em `7c6ce3a`. Base local anterior preservada em stash identificado
no relatório. 43 testes existentes aprovados em SQLite, com limitações explícitas.
Foram reproduzidos problemas de fechamento pelo admin, CSRF anônimo, mídia de QR,
preço negativo, filtro de data, rota do garçom e schema. Também foi demonstrada
uma escrita desatualizada que reativa uma sessão paga por interleaving simulado.

Plano e matriz: `docs/AVALIACAO_E_PLANO_2026-10-23.md`.

## Nota de versão e correções

Este prompt substitui o recorte antigo de apenas preparar a base: agora o objetivo
é planejar a conclusão de todo o MVP. Nenhuma regra de negócio foi corrigida nesta
etapa. As correções futuras devem registrar o problema, a alteração do prompt e
os testes de regressão correspondentes, sem afirmar que foram realizadas antecipadamente.
