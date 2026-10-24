# Etapa 4 — Garçom e fechamento

Contexto: etapa 3 enviada em c40f7b8. Implementar a interface real /garcom/ com
login/perfil, mapa de mesas, abertura de sessão, entregas e contas por polling.
Usar os serviços validados; não duplicar regras em JavaScript ou adicionar pagamento real.

Criar conferência de conta com cancelados sem cobrança, seleção Pix/cartão/dinheiro,
aprovação simulada e liberação da mesa. Sessão vazia ou só cancelada pode encerrar
sem cobrança. Mostrar pendências e bloquear confirmação até entrega/cancelamento.
Manter proteção no servidor mesmo quando botões estiverem desabilitados.

Aceite: fluxo completo com cliente sem login e equipe em seus perfis, repetição
de pagamento sem segunda conta, três métodos, erro de método, estados pendentes,
encerramento sem cobrança e rollback de falha. Coletar estáticos antes dos testes
que usam o manifesto de produção. Validar navegador na etapa 6.
