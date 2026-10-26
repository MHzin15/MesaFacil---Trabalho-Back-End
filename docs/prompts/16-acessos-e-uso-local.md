# Acessos e demonstração local simplificada

Contexto: o usuário pediu explicitamente cadastrar as senhas dos perfis locais,
receber a relação de acessos e um processo de demonstração mais fácil de seguir.

Escopo: garantir admin/admin123, cozinha/cozinha123 e garcom/garcom123 no banco
local e validar login por formulário com CSRF. Guardar os acessos reais do banco
e o link UUID da mesa em `.local/ACESSOS_LOCAIS.md`, já ignorado pelo Git; não
versionar senha real de PostgreSQL, SECRET_KEY ou tokens de mesas.

Simplificar docs/DEMONSTRACAO.md para ligar servidor, entrar no admin, abrir mesa,
montar pedido, preparar, entregar e pagar. Usar admin em várias abas no primeiro
ensaio evita confusão com logins compartilhados; explicar como testar perfis
individuais separadamente. Manter o ensaio detalhado em ENSAIO_COMPLETO.md.

Adicionar link administrativo para abrir o cardápio da mesa sem precisar ler o QR
no próprio computador. Preservar UUID, permissões, API e todas as regras do pedido.
Verificar links autenticados e clientes anônimos; registrar commit e push.
