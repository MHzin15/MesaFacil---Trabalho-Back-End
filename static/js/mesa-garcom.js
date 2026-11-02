'use strict';
(() => {
  const {api, escape, money, poll, statusNames} = MF;
  const byId = id => document.getElementById(id);
  const mesaPath = `/mesa/${document.body.dataset.mesa}/`;
  const base = `/api/mesa/${document.body.dataset.mesa}/`;
  const views = {
    cardapio: {path:mesaPath, title:'Cardápio', description:'Consulte os produtos disponíveis para esta mesa.'},
    pedidos: {path:mesaPath + 'pedidos/', title:'Pedidos', description:'Acompanhe o preparo e a entrega dos pedidos desta mesa.'},
    conta: {path:mesaPath + 'conta/', title:'Contas', description:'Confira o consumo da mesa e acesse o fechamento no salão.'},
  };
  let products = [], selected = null, search = '', lastOrders = '', lastMenu = '', lastBill = '';
  function showView(view, navigate = false) {
    if (!Object.hasOwn(views, view)) return;
    if (navigate) history.pushState(null, '', views[view].path);
    document.body.dataset.clientView = view;
    document.querySelectorAll('[data-client-screen]').forEach(panel => { panel.hidden = panel.dataset.clientScreen !== view; });
    document.querySelectorAll('[data-client-link]').forEach(link => {
      if (link.dataset.clientLink === view) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    byId('client-title').textContent = views[view].title;
    byId('client-description').textContent = views[view].description;
    document.title = `${views[view].title} · Mesa ${document.querySelector('.table-tag strong').textContent} · MesaFácil`;
    window.scrollTo(0, 0);
  }
  document.addEventListener('click', event => {
    const link = event.target.closest('a[data-client-link]');
    if (link && event.button === 0 && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) {
      event.preventDefault(); showView(link.dataset.clientLink, true);
    }
    const category = event.target.closest('button[data-category]');
    if (category) {
      selected = category.dataset.category ? Number(category.dataset.category) : null;
      document.querySelectorAll('[data-category]').forEach(button => button.classList.toggle('active', button === category));
      renderProducts();
    }
  });
  window.addEventListener('popstate', () => {
    const view = Object.keys(views).find(name => views[name].path === location.pathname);
    if (view) showView(view);
    else location.replace(views.pedidos.path);
  });
  const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  function renderProducts() {
    const visible = products.filter(p => (selected === null || p.categoria === selected) && normalize(`${p.nome} ${p.descricao}`).includes(normalize(search)));
    byId('menu-results').textContent = `${visible.length} produto${visible.length === 1 ? '' : 's'}`;
    byId('produtos').innerHTML = visible.map(p => `<article class="product-card ${p.disponivel ? '' : 'unavailable'}"><div class="product-image">${p.foto ? `<img src="${escape(p.foto)}" alt="${escape(p.nome)}" loading="lazy">` : `<span class="food-placeholder" aria-hidden="true">${escape(p.nome.charAt(0))}</span>`}${!p.disponivel ? '<span class="unavailable-tag">Indisponível</span>' : ''}</div><div class="product-body"><h3>${escape(p.nome)}</h3><p>${escape(p.descricao)}</p><div class="product-footer"><strong>${money(p.preco)}</strong><span class="small muted">${p.disponivel ? 'Disponível' : 'Indisponível'}</span></div></div></article>`).join('') || '<p class="empty-state">Nenhum produto encontrado para esta busca.</p>';
  }
  document.addEventListener('error', event => {
    const img = event.target;
    if (!(img instanceof HTMLImageElement) || !img.closest('.product-image')) return;
    const fallback = document.createElement('span');
    fallback.className = 'food-placeholder'; fallback.textContent = img.alt.charAt(0);
    fallback.setAttribute('aria-hidden', 'true'); img.replaceWith(fallback);
  }, true);
  byId('buscar-produto').addEventListener('input', event => { search = event.target.value.trim(); renderProducts(); });
  async function refresh() {
    try {
      const [mesa, categories] = await Promise.all([api(base + '?equipe=1'), api('/api/cardapio/')]);
      byId('session-label').textContent = mesa.sessao_ativa ? 'Sessão aberta' : 'Sem sessão aberta';
      byId('session-warning').hidden = mesa.sessao_ativa;
      byId('session-message').textContent = 'O primeiro pedido do cliente abre o atendimento automaticamente.';
      const menuSignature = JSON.stringify(categories);
      if (lastMenu !== menuSignature) {
        products = categories.flatMap(c => c.produtos);
        byId('categorias').innerHTML = `<button data-category="" class="${selected === null ? 'active' : ''}">Todos</button>` + categories.map(c => `<button data-category="${c.id}" class="${selected === c.id ? 'active' : ''}">${escape(c.nome)}</button>`).join('');
        lastMenu = menuSignature; renderProducts();
      }
      const [orders, bill] = mesa.sessao_ativa ? await Promise.all([api(base + 'pedidos/?equipe=1'), api(base + 'conta/?equipe=1')]) : [[], null];
      const ordersSignature = JSON.stringify(orders);
      if (ordersSignature !== lastOrders) { byId('lista-pedidos').innerHTML = MF.renderOrders(orders, {mostrarComanda:true}); lastOrders = ordersSignature; }
      byId('nav-orders-count').textContent = orders.length;
      byId('nav-orders-count').hidden = !orders.length;
      const billSignature = JSON.stringify(bill);
      if (billSignature !== lastBill) {
        byId('conta-total').textContent = money(bill?.valor_total || 0);
        byId('conta-quantidade').textContent = bill ? `${bill.pedidos.length} pedido${bill.pedidos.length === 1 ? '' : 's'} nas comandas abertas` : 'Nenhuma sessão aberta.';
        byId('resumo-conta').innerHTML = bill?.pedidos.length ? bill.pedidos.map(p => `<div class="bill-order"><div class="bill-row"><div><strong>Comanda #${p.sessao} · Pedido #${p.id}</strong><p class="small muted mb-0">${statusNames[p.status]}${p.status === 'CANCELADO' ? ' · sem cobrança' : ''}</p></div><strong>${money(p.status === 'CANCELADO' ? 0 : p.valor_total)}</strong></div>${MF.itemList(p)}</div>`).join('') : '<p class="empty-state">Nenhum pedido nesta sessão.</p>';
        byId('gerenciar-conta').hidden = !bill?.conta_solicitada;
        byId('conta-status').textContent = !bill ? 'Nenhum atendimento aberto nesta mesa.' : bill.conta_solicitada ? 'Fechamento solicitado. Confira e finalize no painel de contas.' : 'Esta mesa ainda não solicitou o fechamento da conta.';
        lastBill = billSignature;
      }
      byId('client-error').hidden = true;
    } catch (error) {
      byId('client-error-message').textContent = error.message;
      byId('client-error').hidden = false;
    }
  }
  byId('tentar-novamente').addEventListener('click', refresh);
  poll(refresh);
})();
