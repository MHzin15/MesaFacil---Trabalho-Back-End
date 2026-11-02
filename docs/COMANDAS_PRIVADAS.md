# Comandas privadas — 02/11/2026

## Experiência do cliente

1- O cliente lê o QR da mesa, escolhe produtos e envia o pedido, sem login,
senha, código ou presença do garçom. Esse primeiro pedido cria sua comanda.

2- Para consumir junto, toca em **Compartilhar comanda** e mostra o QR no celular
ou envia o link. O familiar confirma **Entrar nesta comanda**. Os pedidos dos dois
aparecem na mesma conta; os carrinhos ainda não enviados continuam por aparelho.

3- Quem prefere pagar separado usa o QR da mesa e começa sua própria comanda.
O cliente também pode escolher **Começar conta separada**. Pedidos já enviados
não são transferidos; as comandas às quais ele já tem acesso ficam no seletor.

4- A equipe recebe mesa, número da comanda e pedido. O pagamento encerra somente
a comanda escolhida. As outras comandas da mesa continuam abertas. O pagamento
atual continua simulado.

5- O próximo grupo cria outra comanda. O navegador anterior não passa a ver sua
conta, mesmo ao recarregar o QR ou escolher começar um novo atendimento.

## Patch: autorização privada

- **Risco original:** o link público da mesa autorizava o consumo e a consulta da
  conta compartilhada, permitindo acesso intencional por alguém com link salvo.
- **Solução:** a mesa identifica o destino da entrega. Cada comanda possui um
  acesso aleatório próprio, guardado na sessão do navegador. O rascunho é criado
  na primeira visita; a comanda no banco nasce apenas no primeiro pedido válido.
  A consulta não seleciona a primeira conta ativa da mesa. IDs numéricos de
  contas não concedem acesso. Novas comandas têm acessos independentes.
- **Impacto:** `SessaoMesa` passa a representar uma comanda; podem existir várias
  ativas por mesa. O acesso individual possui restrição única no banco. As
  transações continuam bloqueando mesa antes de comanda e pedido, evitando
  duplicação em pedidos simultâneos e mistura de cobranças.

## Patch: convite entre familiares

- **Risco original:** entrar automaticamente numa conta pela mesa mistura grupos.
- **Solução:** somente um participante da comanda pode gerar um convite pelo
  botão de compartilhar. O token do convite é diferente do acesso permanente
  da comanda, tem validade de 15 minutos e é recusado depois do encerramento.
  O GET do convite apenas mostra a confirmação: prévias de mensagens e leitores
  de link não inscrevem ninguém. A entrada exige POST com CSRF válido.
- **Impacto:** reutiliza a biblioteca de QR existente, sem nova dependência.
  O PNG é servido por endpoint privado, sem arquivo público em mídia ou cache.
  Respostas não são armazenadas e a política de referência impede enviar o
  endereço do convite a sites externos, mantendo formulários CSRF funcionais.
  Quem já entrou pode continuar até fechar a conta, mesmo após expirar o convite.
  O cliente deve enviar o convite somente às pessoas com quem vai consumir.

## Patch: salão, cozinha e gestão

- **Risco original:** telas e modelos presumiam uma única conta por mesa. Ao
  permitir várias, uma seleção ambígua poderia encerrar a conta errada.
- **Solução:** mapa de mesas e fila de fechamento mostram cada comanda e seu
  número. Pedidos de cozinha/entrega identificam a comanda. A conferência e o
  pagamento usam o ID da comanda escolhida, versão e total conferidos.
  O resumo de todas as comandas da mesa é somente leitura para garçom/admin.
- **Impacto:** clientes não podem habilitar a consulta da equipe por parâmetro.
  O indicador de mesas ocupadas conta mesas distintas, não comandas. A mesa fica
  ocupada enquanto existir outra comanda aberta. As consultas de listagem usam
  a carga antecipada das comandas para manter o número de consultas estável.
  Divisão parcial de uma mesma conta e pagamento misto não fazem parte do patch.

## Migrações e publicação

- `0007`: versão de conferência e justificativa de cancelamento excepcional.
- `0008`: acesso individual por comanda, convites e remoção da restrição de uma
  única comanda ativa por mesa. Preserva contas, pedidos e histórico existentes.
- As permissões antigas de acesso público não são convertidas em acesso privado
  a contas existentes: o sistema anterior não identificava seus participantes.
  Publique com os atendimentos do fluxo antigo encerrados para evitar perda de
  acesso dos clientes em consumo. O histórico da equipe permanece disponível.
- O build do Render coleta os arquivos estáticos; o start já aplica migrations.
  Publicar interface e backend da mesma revisão. Ainda não houve push/deploy.

## Validação e limites

- Suíte completa no PostgreSQL: **166 testes e 158 subtestes aprovados**, incluindo
  pedidos simultâneos na mesma comanda e de famílias separadas.
- Testes entre navegadores independentes cobrem isolamento de conta, ingresso
  explícito, token expirado, CSRF e origem externa, QR privado, alternância entre
  próprias comandas, fechamento individual e restrição da consulta da equipe.
- Conferência no navegador: primeiro pedido sem funcionário, QR de convite
  renderizado e entrada de familiar em sessão independente do navegador dono.
- Um link público de mesa salvo pode criar um pedido separado: QR fixo não
  comprova presença física. Ele não dá acesso às contas de outros grupos.
- Apagar cookies ou perder a sessão do navegador exige um convite válido de
  outro participante para recuperar uma comanda em andamento. O convite é uma
  credencial de acesso e não deve ser publicado ou enviado a desconhecidos.
