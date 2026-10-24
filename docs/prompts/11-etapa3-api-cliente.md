# Etapa 3 — API, cliente e cozinha

Contexto: etapa 2 enviada em e64f14c. Completar contratos reais de todas as views,
sem usar um schema genérico para esconder diferenças de resposta. Valores em
Decimal, filtros válidos, listas vazias estáveis, snapshots e cancelados sem cobrança.

Cliente: atualizar disponibilidade por polling, recuperar erros iniciais/reconexão,
revisar preços antes de enviar e usar chave de envio estável para repetição após
falha de rede. Não considerar pedido enviado offline, nem enviar novamente com
outra chave só porque a resposta se perdeu. Preservar sessão esperada e CSRF.

Aceite: schema completo validado em modo estrito sem erros/avisos; regressões de
idempotência, totais e cancelados aprovadas no PostgreSQL, além da suíte existente.
Validação em navegador e dispositivos permanece na etapa de aceitação final.
