# Revisão do frontend — 25/10/2026

Solicitação: tornar o uso mais intuitivo no desktop e corrigir a inclusão de
produtos. Continuação do plano original, sem novas regras de negócio ou opcionais.

## Defeito reproduzido

Em Chrome, 1920×1080, a foto de produto ultrapassava sua área de 145 px e tinha
282 px de altura. Ela cobria descrição/preço/botão. O teste de clique identificou
um IMG sobre o centro do botão e expirou por interceptação de eventos de mouse.

Corrigido o dimensionamento com imagem posicionada dentro de uma área limitada,
recorte e object-fit. Na versão nova, imagem e área têm 160 px no desktop e o
elemento atingido no centro da ação é o próprio BUTTON. Não foi usado clique
forçado nem retirada de eventos como forma de contornar a sobreposição.

## Ajustes de uso

| Tela | Mudança |
| --- | --- |
| Cardápio | Botões Adicionar, busca sem depender de acentos, categorias e limpeza de filtros |
| Sessão | Aviso de mesa fechada e explicação do bloqueio de pedidos; link do salão para perfis autorizados |
| Personalização | Preço do produto e total com quantidade/adicionais, área de conteúdo com rolagem e ação acessível |
| Carrinho | Organização no desktop, limites de quantidade, atalhos e orientação da próxima ação |
| Revisão | Voltar às escolhas e mensagens de erro dentro do diálogo, acima do fundo modal |
| Reconexão | Erro persistente de carregamento com Tentar novamente |
| Carrinho salvo | Atualização dos preços após restaurar a sessão, sem depender de outra mudança no cardápio |
| Equipe | Links Salão/Cozinha/Administração para o administrador, usuário atual visível |
| Salão | Mesas ao lado de entregas/contas, contadores e acesso direto ao cardápio da mesa |
| Cozinha | Orientação explícita de aceitar, preparar e marcar pronto; itens com leitura maior |
| PWA | Cache v3; estáticos sem hash consultam rede antes do cache para refletir mudanças locais |

## Reprodução dos testes

Siga [VALIDACAO_NAVEGADOR.md](VALIDACAO_NAVEGADOR.md), em banco isolado, com a ordem:
check_flow → check_regressions → check_desktop → check_pwa.
Não execute os cenários de pedidos/pagamentos no banco de uso do restaurante.

O defeito inicial também foi reproduzido com leitura do cardápio no servidor local,
sem enviar pedido nem alterar o atendimento. A revisão preservou o ajuste manual
que já existia em docs/DEMONSTRACAO.md.

Evidências de navegador são locais em `.tmp/`: browser-result.json,
browser-regressions.json, desktop-result.json, pwa-result.json e screenshots.
Nenhuma senha, cookie ou UUID privado foi acrescentado à documentação pública.

## Resultado da bateria

- PostgreSQL: **87 testes aprovados**, incluindo concorrência; check, migrations,
  estáticos, OpenAPI estrito e dependências também aprovados.
- Chrome: inclusão/remoção, imagem contida, ausência de rolagem horizontal e ação
  da personalização acessível em 1920×1080, 1440×900, 1366×768, 1024×768 e 390×844.
- Fluxo completo pelas telas: cartão simulado no cenário móvel e Pix simulado
  no cenário desktop; pedidos entregues, conta paga e mesa liberada.
- Busca/categorias, teclado, sessão fechada, carrinho longo, indisponibilidade
  durante personalização, recuperação de carregamento e erro de envio aprovados.
- Carrinho salvo com preços desatualizados passou a usar os valores atuais.
- Reajuste exigindo nova revisão, resposta perdida sem duplicar, cancelamento
  inicial e encerramento sem cobrança continuaram aprovados.
- PWA: manifesto/instalabilidade sem erros, offline funcional, POST offline
  bloqueado e nenhuma resposta privada no Cache API.
- Nenhum erro JavaScript nas baterias. Isso continua sendo teste de navegador;
  não afirma instalação em celular físico ou execução Docker/Gunicorn.
