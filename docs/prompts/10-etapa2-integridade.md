# Etapa 2 — Integridade e segurança

Contexto: etapa 1 validada e enviada em 549511a. Implementar os problemas de alta
prioridade da auditoria antes de expandir as telas. Centralizar operações em
serviços transacionais; mesmas regras para API/admin; CSRF também para anônimos;
contexto de mesa e sessão esperada; QR privado; perfis consistentes; constraints.

Aceite: regressões do fechamento irregular, CSRF, acesso entre mesas/sessões,
preço negativo e filtro inválido; testes reais de concorrência em PostgreSQL para
abertura, transição e pedido versus pagamento. Não usar mocks como substitutos
dos locks reais. Manter as cinco etapas do pedido e cancelamento antes do preparo.

Correções de regras: o admin não pode mais fechar/reabrir sessões por edição de
campos; solicitar conta bloqueia a sessão e atualiza apenas o campo de solicitação,
evitando reabrir uma sessão paga. Nenhum QR é gravado em mídia pública. Pedidos
exigem contexto estabelecido pelo QR e o ID da sessão esperada, revalidado sob lock.

Atualização de instalação: executar migrate e sync_roles. O acesso ADMIN é um papel
com permissões de equipe, sem conceder is_superuser. O admin de usuários esconde
superusuários e campos de elevação de privilégios de administradores comuns.
