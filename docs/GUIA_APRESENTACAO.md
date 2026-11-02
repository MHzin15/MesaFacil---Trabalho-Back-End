# MesaFácil — guia de apresentação

Use as frases abaixo como apoio para falar. Mostre as telas enquanto explica.
As observações de estado servem para o ensaio; não precisam ser lidas ao público.

1- **O que é o projeto**

“O MesaFácil é um sistema de pedidos para restaurantes. O cliente lê o QR Code
da mesa, vê o cardápio e faz o pedido pelo celular.”

2- **Qual problema queremos resolver**

“O cliente pode esperar muito para ser atendido. Também podem ocorrer erros ao
anotar um pedido. Nossa proposta é deixar o cliente escolher e confirmar o que
quer, sem esperar o garçom para fazer o pedido.”

3- **Como o cliente faz o pedido**

“O cliente abre o cardápio, escolhe o produto, ajusta a quantidade e inclui
adicionais ou observações. Depois, confere o carrinho e confirma o envio.”

Mostre: cardápio → produto → carrinho → revisão → pedidos.

4- **Como a cozinha trabalha**

“A cozinha recebe o pedido na tela. A equipe acompanha as etapas e marca quando
o preparo começa e quando o pedido fica pronto.”

Mostre a mudança de um pedido recebido para em preparo e depois pronto.

5- **Qual é o papel do garçom**

“O garçom acompanha as mesas, leva os pedidos prontos e ajuda no fechamento da
conta. O cliente faz o pedido; o garçom cuida do atendimento no salão.”

Problema identificado: o garçom via carrinho e botões de pedido como se fosse cliente.
Solução: retiramos esses controles e bloqueamos a criação de pedidos por esse perfil.

6- **Como o dono controla o restaurante**

“O gestor tem uma área própria. Ele pode cadastrar funcionários e mesas,
alterar o cardápio, ajustar preços e consultar os pedidos e recebimentos.”

Mostre também a suspensão de acesso e a redefinição de senha de um funcionário.
Use dados de demonstração.

7- **Melhoria da tela de gestão**

Problema identificado: a administração era técnica e difícil para a rotina do restaurante.
Solução: criamos telas por tarefa, com textos simples e o mesmo visual do site.

“O gestor encontra as ações pelo que precisa fazer, sem conhecer detalhes do banco.”

8- **Melhoria do cardápio**

Problema identificado: faltavam fotos e algumas escolhas não ficavam claras.
Solução: incluímos fotos de exemplo e uma escolha de sabor para refrigerante em lata.

“O cliente vê melhor os produtos e informa qual refrigerante quer antes de adicionar.”

9- **Proteção dos acessos**

Problema identificado: era preciso reforçar senhas e limitar tentativas de entrada.
Solução: aplicamos regras de senha e limites de tentativas de login.

“Cada função tem acesso ao que precisa. As permissões também são conferidas pelo sistema.”

10- **Preço correto e pedido sem duplicação**

Problema identificado: um preço pode mudar durante a escolha e um envio pode ser repetido.
Solução: o sistema confere o total e reconhece o reenvio do mesmo pedido.

“O cliente revisa o valor antes de enviar. Se a resposta demorar, o mesmo envio
não deve gerar duas cobranças.”

11- **Pedido sem precisar abrir a mesa com o garçom**

Problema identificado: o cliente precisava esperar a equipe abrir o atendimento.
Solução: o primeiro pedido válido abre uma comanda privada automaticamente.

“Ler o QR abre o cardápio. Confirmar o primeiro pedido abre a própria comanda,
sem senha, cadastro ou aprovação do garçom.”

Estado para o ensaio: fluxo já testado localmente; publicação ainda pendente.

12- **Conta privada de cada família**

Problema identificado: o link da mesa podia dar acesso à conta de outro grupo.
Solução: cada pessoa pode começar uma comanda privada. Para pedir
na mesma conta, os familiares entram por um link ou QR compartilhado por alguém
da própria família.

“A mesa indica onde entregar. A comanda guarda os pedidos daquele grupo.
Pode haver mais de uma comanda na mesma mesa, sem misturar os valores.”

“Para pedir na mesma conta com a família, eu toco em Compartilhar comanda.
O familiar abre o convite e confirma que quer entrar. Não precisa do garçom.”

O convite vale por 15 minutos e deixa de funcionar quando a comanda é encerrada.
Quem já possui mais de uma comanda pode alternar entre as próprias contas.
Abrir apenas o QR da mesa não mostra a conta de outras pessoas.

Estado para o ensaio: implementado e testado localmente; publicação ainda pendente.

13- **Conferência antes de fechar a conta**

Problema identificado: podiam entrar pedidos novos enquanto a conta era conferida.
Solução: solicitar a conta bloqueia novos pedidos naquela conta. A equipe pode
retomar o consumo, caso o cliente queira pedir mais.

“Se a conta mudar, o sistema exige uma nova conferência do total antes de confirmar.”

Estado para o ensaio: correções já testadas localmente; publicação ainda pendente.

14- **Como resolver um erro depois de começar o preparo**

Problema identificado: faltava um caminho para tratar um pedido indevido após iniciar o preparo.
Solução: o gestor pode fazer um cancelamento excepcional, com justificativa.

“O motivo, o responsável e o horário ficam no histórico. O pedido cancelado sai
da cobrança. Essa ação não desfaz um pagamento já concluído.”

Estado para o ensaio: correção já testada localmente; publicação ainda pendente.

15- **Pagamento da demonstração**

“Nesta versão, o pagamento é simulado. Selecionamos Pix, cartão ou dinheiro para
mostrar o fechamento. O sistema não faz uma cobrança bancária real.”

“Quando a equipe confirma o pagamento no sistema, somente a comanda escolhida
é encerrada. As outras comandas da mesma mesa continuam abertas.”

16- **Como foi construído e conferido**

“Usamos Python e Django para as regras do sistema e PostgreSQL para guardar os
dados. As telas funcionam no navegador do computador e do celular.”

“Criamos testes para conferir permissões, preços, etapas do pedido e operações
feitas ao mesmo tempo. Também conferimos o uso pelas telas.”

Evidência para o ensaio: 166 testes e 158 subtestes aprovados no PostgreSQL.

Não diga que o sistema funciona sem internet: o envio de pedidos e o pagamento
precisam de conexão. O modo offline permite consultar conteúdo já salvo.

17- **Ordem da demonstração**

“Primeiro, mostro o cliente escolhendo e enviando um pedido. Depois, mostro a
cozinha preparando e o garçom confirmando a entrega. Por fim, solicito a conta
e confirmo o pagamento simulado. Encerro mostrando o cadastro e os preços na gestão.”

Use dois navegadores para mostrar o compartilhamento entre familiares. Depois,
abra o QR da mesa em outro navegador e mostre que ele não recebe a conta da família.
No salão, mostre o número de cada comanda e o fechamento de apenas uma delas.

18- **O que fica para as próximas etapas**

“Ainda queremos incluir divisão de pagamentos, transferência de mesa, alertas de
atendimento e controle de limpeza antes de liberar a mesa. Também falta integrar
um meio de pagamento real.”

Esses recursos são propostas; não devem ser apresentados como disponíveis.

Limite atual: um link de mesa salvo ainda pode ser usado para criar um pedido
separado. O sistema protege as contas privadas, mas não confirma se a pessoa
está fisicamente no restaurante.

19- **Como encerrar a apresentação**

“O MesaFácil organiza o caminho entre cliente, cozinha, garçom e gestor.
O objetivo é reduzir a espera e dar mais clareza aos pedidos, mantendo o cliente
livre para pedir pelo próprio celular.”

Preparação do roteiro: 02/11/2026. A gestão e as melhorias anteriores já foram
enviadas ao repositório. As mudanças recentes de fluxo e comandas privadas estão
implementadas e validadas localmente, ainda sem push ou publicação. Confira se
o ensaio está usando essa versão antes de apresentar os itens 11 a 14.
