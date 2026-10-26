# Revisão de frontend com foco em desktop

Contexto: o usuário considerou a interface pouco intuitiva e relatou que não
conseguia adicionar produto ao pedido, usando principalmente desktop.

Escopo: reproduzir no navegador, corrigir o bloqueio e melhorar o fluxo existente
de cardápio, carrinho, envio, cozinha e garçom. Preservar o MVP, APIs, permissões,
CSRF, sessões, snapshots, sequência de estados e pagamentos simulados. Não incluir
opcionais. Preservar alterações manuais já existentes em docs/DEMONSTRACAO.md.

## Erro confirmado e correção do direcionamento

Os testes anteriores usavam o cliente em viewport móvel e não detectaram que a
foto extrapolava a área reservada no desktop. Em 1920×1080, a área tinha 145 px
de altura, mas a imagem ocupava 282 px e interceptava o botão. O clique real
expirou com a evidência `IMG intercepts pointer events`.

O prompt de revisão passa a exigir cliques reais sem `force`, contenção das fotos,
texto e botões não sobrepostos e testes em cinco resoluções. Corrigir as dimensões
da imagem, não apenas remover seus eventos de mouse ou elevar o z-index do botão.

## Melhorias e aceite

- Botão textual Adicionar, busca com categorias e mensagem de nenhum resultado.
- Explicação persistente da sessão fechada e da revisão desabilitada.
- Preço base e total com quantidade/adicionais dentro da personalização.
- Erros dentro do diálogo: o toast externo ficava atrás da camada modal.
- Revalidar preços do carrinho restaurado antes de permitir o envio.
- Navegação de administrador entre salão/cozinha/admin; link do cardápio no salão.
- Entregas e contas ao lado das mesas em desktop e resumo do atendimento.
- Atualizar o cache do PWA para não manter CSS/JS sem hash antigos no uso local.

Validar PostgreSQL, fluxo completo, reajuste, resposta perdida, cancelamento,
desktop e offline em banco separado. Registrar o defeito original, correções e
limites em docs/REVISAO_FRONT_DESKTOP.md; commit/push somente dos arquivos desta
revisão, deixando o ajuste manual do guia fora do commit.
