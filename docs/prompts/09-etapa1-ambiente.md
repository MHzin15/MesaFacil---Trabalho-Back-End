# Etapa 1 — Ambiente reproduzível

Contexto: continuar o app restaurante no commit 7c6ce3a conforme a avaliação.
Pedido: implementar as seis etapas, validando, commitando e enviando cada uma antes
de prosseguir. Nesta etapa, alinhar .env, PostgreSQL e dependências; separar testes
rápidos de integração; Docker/Compose e execução Windows; seed seguro e repetível.

Restrições: preservar dados e segredos locais; não alterar bancos de outros projetos;
sem SQLite na aplicação; sem recursos opcionais. Não declarar etapas futuras concluídas.

Aceite: instalação, check, migrations, seed repetido, collectstatic e suíte existente
em PostgreSQL. Versões estáveis consultadas no PyPI em 23/10/2026 e fixadas com ==.
Gunicorn somente em Linux/container; Python mínimo 3.12.
