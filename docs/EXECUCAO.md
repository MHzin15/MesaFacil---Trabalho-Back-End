# Execução do plano

Guia: [avaliação de 23/10/2026](AVALIACAO_E_PLANO_2026-10-23.md).
Cada etapa terá commit, push e evidência de validação antes da seguinte.

| Etapa | Situação | Evidência |
| --- | --- | --- |
| 1. Ambiente | Concluída | PostgreSQL 18.6: migrations, seed repetido, collectstatic e 45 testes aprovados; configuração rápida também aprovada. Compose preparado, execução Docker não disponível nesta máquina. |
| 2. Segurança e integridade | Concluída | 57 testes aprovados em PostgreSQL, incluindo 3 corridas com conexões reais; CSRF anônimo, QR privado, contexto de sessão, admin protegido e constraints. |
| 3. API, cliente e cozinha | Concluída | 62 testes em PostgreSQL; OpenAPI estrito sem erros/avisos; envio idempotente, disponibilidade no polling e totais padronizados. Validação de navegador na etapa 6. |
| 4. Garçom e pagamento | Concluída | 68 testes PostgreSQL; painel, conta de atendimento, três métodos, fluxo completo, repetição e rollback. Revisão de navegador na etapa 6. |
| 5. PWA | Concluída | 72 testes PostgreSQL; Chrome sem erros de instalabilidade/manifesto, SW ativo, offline e cardápio salvo testados; cache privado ausente. Celular físico permanece na demonstração final. |
| 6. Aceitação | Pendente | |
