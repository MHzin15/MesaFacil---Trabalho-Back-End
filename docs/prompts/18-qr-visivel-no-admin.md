# Tornar o QR Code fácil de encontrar

Contexto: o usuário não encontrou a geração do QR ao preparar a apresentação.
O download já existia dentro do cadastro individual da mesa, com pouca visibilidade.

Escopo: incluir a ação existente Baixar QR Code diretamente na lista de mesas do
admin e destacá-la como botão. O PNG é gerado na hora com PUBLIC_BASE_URL e UUID;
não criar outro fluxo nem expor o download sem perfil administrativo.

Aceite: login de administrador acessa a lista com botão por mesa e baixa PNG;
download anônimo continua bloqueado. Informar link direto da Mesa 1 ao usuário e
preservar sua edição manual em docs/DEMONSTRACAO.md.
