# Instalação e funcionamento offline

O manifesto é `/manifest.webmanifest`; o service worker fica na raiz em
`/service-worker.js`, com escopo `/`. As páginas incluem registro e botão
**Instalar app**, exibido quando o navegador oferece instalação. Também é possível
instalar pelo menu do navegador. Em iOS, use Compartilhar → Adicionar à Tela de Início.

O app abre na entrada do restaurante. Para identificar uma mesa, abra seu QR Code.
O contexto de mesa não é escolhido por número nem fixado no manifesto.

## Política de cache

- Precache: página offline pública, manifesto, CSS, Bootstrap, ícones e script offline.
- Recursos em `/static/`: cache público; o cardápio `/api/cardapio/` tenta a rede primeiro.
- Navegação sem rede: página amigável com consulta ao cardápio salvo, se já carregado.
- Pedidos, contas, equipe, HTML autenticado e QR privado nunca são armazenados pelo SW.
- Escritas não são interceptadas, guardadas em fila nem reenviadas automaticamente.
- A página offline é renderizada sem request, usuário ou token CSRF no conteúdo.

Ao reconectar, o cliente consulta disponibilidade e preços atuais. Dados salvos
são identificados como sujeitos a confirmação, sem permitir realizar pedidos offline.
Ao alterar a política de cache, incremente a versão em `templates/service-worker.js`.

Na revisão de desktop, o cache passou para `mesafacil-public-v3`. Arquivos estáticos
com hash continuam imutáveis e preferem cache. CSS/JS sem hash consultam a rede
primeiro e usam o cache se estiver offline, para que mudanças locais não fiquem
presas numa versão anterior. Dados privados continuam fora do Cache API.

Na navegação separada do cliente (29/10), o cache foi atualizado para v4 e inclui
o CSS público das novas telas. As páginas de carrinho/pedidos/conta continuam
buscadas na rede; não entram no cache. As novas URLs também recebem a página
offline pública quando não há conexão. Não existe fila de pedidos offline.

## Verificação realizada

Chrome 155, perfil exclusivo de teste e viewport 390×844: nenhum erro de manifesto
ou instalabilidade informado pelo navegador, SW ativo, navegação offline funcional,
cardápio salvo legível, POST offline bloqueado e nenhuma resposta privada no Cache API.
Também não houve erro JavaScript. Isso não substitui a demonstração física em celular.

`scripts/check_pwa.cjs` reproduz a verificação em Chrome instalado. Requer Node e
Playwright para testes (validado com 1.62.1), sem introduzi-los no servidor Django.
Com a aplicação no ar, configure `MESAFACIL_URL` se necessário e execute
`node scripts/check_pwa.cjs`. `PLAYWRIGHT_MODULE` permite informar um módulo instalado
fora do projeto. Resultados e perfil ficam em `.tmp/`, fora do versionamento.

## Celular real

Service worker exige HTTPS ou localhost. `http://IP-DO-COMPUTADOR` não é um contexto
seguro no celular. Use endereço HTTPS alcançável, configure PUBLIC_BASE_URL,
ALLOWED_HOSTS e CSRF_TRUSTED_ORIGINS, regenere o QR e acesse nos dois aparelhos.
No ambiente de publicação, DEBUG=False e cookies seguros exigem HTTPS.

Referência: [documentação de service workers](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers).
