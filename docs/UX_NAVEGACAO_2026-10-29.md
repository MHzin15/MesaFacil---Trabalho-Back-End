# Navegação do cliente — 29/10/2026

O usuário aprovou as funcionalidades e pediu separar as áreas que antes ficavam
empilhadas numa página longa. Esta entrega trata da apresentação e navegação.

## Como ficou

| Área | Endereço | Uso |
| --- | --- | --- |
| Cardápio | `/mesa/<UUID>/` | Buscar produtos e personalizar os itens |
| Carrinho | `/mesa/<UUID>/carrinho/` | Ajustar quantidades, remover itens, observar e revisar |
| Meus pedidos | `/mesa/<UUID>/pedidos/` | Acompanhar cada etapa com indicadores e rótulos |
| Conta | `/mesa/<UUID>/conta/` | Consultar todos os pedidos da sessão e solicitar fechamento |

Apenas a área escolhida fica visível. Cada navegação abre no topo e destaca o
destino atual. As URLs aceitam acesso direto e atualização; links antigos com
âncora são convertidos para a tela correspondente. Voltar/avançar funcionam sem
perder o rascunho. Após envio confirmado, o cliente vai para Meus pedidos.

No desktop, o carrinho e a conta têm resumo lateral. No celular, a navegação fica
fixa na parte inferior e total/ação principal aparecem acima dela. Cardápio tem
atalho para o carrinho com quantidade e total. Produtos ficam em lista compacta
no celular; pedidos têm progresso identificado por etapa, além da cor.

Itens, adicionais e observação geral são mantidos ao alternar telas ou recarregar.
A consulta automática de status permanece ativa. A troca/encerramento da sessão
continua limpando o rascunho exibido. O QR administrativo continua no cabeçalho.

## Limites da mudança

Modelos, migrations, serviços, contratos REST, permissões, preços, idempotência,
pagamento e estados do pedido não foram alterados. Os novos caminhos Django só
selecionam a tela inicial e mantêm o contexto da mesa e respostas `no-store`.
O PWA foi atualizado para cache v4 de arquivos públicos, sem cache de HTML privado.

Os commits remotos até 4291c8b foram incorporados antes do trabalho. A melhoria
fica em `codex/client-screen-navigation`, pois a main está ligada ao deploy
automático do Render. Esta entrega não representa publicação no site remoto.
O ajuste manual existente em docs/DEMONSTRACAO.md foi preservado fora do commit.

## Validação

- Seis testes de páginas aprovados, com dez subtestes: rotas diretas, somente a
  tela selecionada visível no HTML inicial, contexto da mesa e bloqueio de mesa inativa.
- Fluxo completo pelas telas até cartão simulado; bateria desktop com Pix,
  disponibilidade, cancelamento, reajuste e resposta perdida sem duplicar pedido.
- Navegação em 1920×1080, 1366×768 e 390×844: URLs, topo, voltar/avançar,
  preservação de busca, itens, adicionais e observação, recarga e links diretos.
- Clique de inclusão/remoção e personalização também em 1440×900 e 1024×768;
  fotos contidas e ausência de rolagem horizontal.
- PWA: manifesto/instalabilidade, offline, reconexão e ausência de cache privado
  aprovados no Chrome. Nenhum erro JavaScript nas baterias.
- Checks de Django, migrations, collectstatic, OpenAPI estrito e pip check aprovados.

A suíte geral em PostgreSQL executou **98 testes: 97 aprovados e uma falha já
existente na base**. Antes de editar a interface, a mesma falha foi reproduzida
com pytest: `test_missing_or_weak_initial_password_stops_without_creating_data`,
no cenário de senha fraca do bootstrap do Render. A configuração atual não gera
o erro esperado nesse caso. Ela foi mantida fora desta alteração de UI/UX;
portanto esta entrega não declara a suíte geral integralmente aprovada.

Resultados locais: `.tmp/navigation-result.json`, `.tmp/browser-result.json`,
`.tmp/browser-regressions.json`, `.tmp/desktop-result.json`, `.tmp/pwa-result.json`
e capturas em `.tmp/screens/`. Os testes usam banco exclusivo, sem mudar os pedidos
do usuário. Reprodução: [VALIDACAO_NAVEGADOR.md](VALIDACAO_NAVEGADOR.md).
