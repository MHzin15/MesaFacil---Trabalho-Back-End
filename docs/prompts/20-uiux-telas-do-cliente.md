# UI/UX — telas separadas para o cliente

Contexto: o usuário aprovou as funcionalidades, mas considerou confusa a página
longa com cardápio, carrinho, pedidos e conta. Pediu melhorar apenas a experiência.

Escopo: dar a cada uma dessas quatro áreas uma tela e URL próprias, mantendo o
QR atual como entrada no cardápio. Navegação deve mostrar uma área por vez, abrir
no topo, indicar a seção ativa e funcionar com voltar/avançar e acesso direto.
Depois do envio, abrir Meus pedidos, sem rolar até outra seção.

Preservar os itens, os adicionais e a observação do carrinho ao navegar/atualizar;
manter busca e categoria ao alternar telas na mesma página. Reorganizar a conta,
deixar o progresso legível e oferecer navegação acessível no desktop e no celular.
Continuar usando Django, Bootstrap e Fetch; sem novas dependências.

Restrições: não alterar modelos, serviços, contratos da API, permissões ou regras
de negócio. Preservar o botão administrativo do QR e a edição manual existente
em docs/DEMONSTRACAO.md. A main passou a ter deploy automático no Render: entregar
em branch própria para revisão, sem publicar automaticamente no ambiente remoto.

Aceite: rotas diretas e mesa inativa, uma tela visível por vez, foco/posição de
rolagem, histórico do navegador, rascunho e observações, fluxo completo, reajuste,
resposta perdida, desktop/celular e PWA. Atualizar testes de navegador para clicar
na navegação real, mantendo todas as asserções de negócio.

A base 4291c8b já apresenta uma falha de validação de senha no bootstrap do Render,
reproduzida antes das alterações. Registrar esse limite sem incluir correção de
backend nesta entrega de UI/UX.
