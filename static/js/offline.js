'use strict';
document.getElementById('offline-menu').addEventListener('click', async () => {
  const node = document.getElementById('saved-menu');
  try {
    const response = await caches.match('/api/cardapio/');
    if (!response) { node.textContent = 'Nenhum cardápio foi salvo neste aparelho. Reconecte para carregar.'; return; }
    const menu = await response.json();
    node.replaceChildren();
    const money = new Intl.NumberFormat('pt-BR', {style:'currency', currency:'BRL'});
    for (const category of menu) {
      const section = document.createElement('section');
      const title = document.createElement('h2'); title.textContent = category.nome; section.append(title);
      for (const product of category.produtos) {
        const item = document.createElement('p');
        item.textContent = `${product.nome} · ${money.format(Number(product.preco))} — informação salva, sujeita a confirmação`;
        section.append(item);
      }
      node.append(section);
    }
  } catch { node.textContent = 'Não foi possível abrir o cardápio salvo. Reconecte e tente novamente.'; }
});
