# QR na página de mesa indicada pelo usuário

Contexto: o usuário esclareceu que procura o botão em `/mesa/<uuid>/`, e não
na listagem do admin. A alteração anterior foi aplicada em outra tela.

Escopo: acrescentar Baixar QR Code no cabeçalho do cardápio da mesa, junto da
identificação da mesa, quando o usuário autenticado tem perfil ADMIN. Reutilizar
o endpoint existente, mantendo sua permissão e a geração do PNG na hora.

Aceite: verificar no navegador a própria página indicada pelo usuário, login
com retorno para a mesa, botão visível e download real. Conferir que cliente
anônimo e equipe sem perfil administrativo continuam sem acesso à ação.
Preservar o ajuste manual existente em docs/DEMONSTRACAO.md.
