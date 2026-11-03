'use strict';
(() => {
  const {money, escape, api, feedback, poll, statusNames, itemList} = MF;
  const token = document.body.dataset.mesa;
  const base = `/api/mesa/${token}/`;
  const byId = id => document.getElementById(id);
  document.addEventListener('error', event => {
    const img = event.target;
    if (!(img instanceof HTMLImageElement) || !img.closest('.product-image')) return;
    const fallback = document.createElement('span');
    fallback.className = 'food-placeholder';
    fallback.setAttribute('aria-hidden', 'true');
    fallback.textContent = img.alt.charAt(0);
    img.replaceWith(fallback);
  }, true);
  let products = [], cart = [], sessionId = null, currentProduct = null, sending = false, selected = null, search = '';
  let draftId = null, access = false, loadedContext = false, closing = false, ended = false, menuSignature = '';
  let menuReady = false, refreshPromise = null, editingIndex = null, removedItem = null;
  const privateUrl = path => `${base}${path}?atendimento_id=${encodeURIComponent(draftId)}`;
  let currentView = document.body.dataset.clientView;
  const mesaPath = `/mesa/${token}/`;
  const views = {
    cardapio: {path:mesaPath, title:'Cardápio', description:'Escolha seus produtos e personalize cada item.'},
    carrinho: {path:mesaPath + 'carrinho/', title:'Seu carrinho', description:'Confira as quantidades e os adicionais antes de enviar.'},
    pedidos: {path:mesaPath + 'pedidos/', title:'Meus pedidos', description:'Acompanhe o preparo e a entrega dos pedidos da sua comanda.'},
    conta: {path:mesaPath + 'conta/', title:'Minha conta', description:'Veja o total da sua comanda e peça o fechamento quando quiser.'},
  };
  function showView(view, navigate = false, focus = false) {
    if (!Object.hasOwn(views, view)) return;
    if (navigate && (location.pathname !== views[view].path || location.hash || location.search)) history.pushState(null, '', views[view].path);
    currentView = view;
    document.body.dataset.clientView = view;
    document.querySelectorAll('[data-client-screen]').forEach(panel => { panel.hidden = panel.dataset.clientScreen !== view; });
    document.querySelectorAll('[data-client-link]').forEach(link => {
      if (link.dataset.clientLink === view) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    byId('client-title').textContent = views[view].title;
    byId('client-description').textContent = views[view].description;
    document.title = `${views[view].title} · Mesa ${document.querySelector('.table-tag strong').textContent} · MesaFácil`;
    byId('cart-shortcut').hidden = !cart.length || view !== 'cardapio';
    if (focus) {
      document.querySelectorAll('dialog[open]').forEach(dialog => dialog.close());
      window.scrollTo(0, 0);
      byId('client-title').focus({preventScroll:true});
    }
  }
  const viewFromPath = () => Object.keys(views).find(view => views[view].path === location.pathname) || 'cardapio';
  document.addEventListener('click', event => {
    const link = event.target.closest('a[data-client-link]');
    if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    showView(link.dataset.clientLink, true, true);
  });
  window.addEventListener('popstate', () => showView(viewFromPath(), false, true));
  const cartSignature = () => JSON.stringify([draftId, cart, byId('observacao-pedido').value]);
  let lastOrders = '', lastBill = '', attempt = null;
  const attemptKey = () => `mf-attempt-${token}-${draftId}`;
  const noteKey = () => `mf-note-${token}-${draftId}`;
  function saveAttempt() { try { if (attempt) sessionStorage.setItem(attemptKey(), JSON.stringify(attempt)); else sessionStorage.removeItem(attemptKey()); } catch {} }
  function optionsAvailable(item, product) {
    const choices = item.opcoes || [];
    return (product.grupos_opcoes || []).every(g => (!g.obrigatorio && !choices.some(c => c.grupo_id === g.id)) || choices.some(c => c.grupo_id === g.id && g.opcoes.some(o => o.id === c.opcao_id))) && choices.every(c => (product.grupos_opcoes || []).some(g => g.id === c.grupo_id && g.opcoes.some(o => o.id === c.opcao_id)));
  }
  const cartAvailable = () => cart.every(i => { const p = products.find(p => p.id === i.produto_id); return p?.disponivel && optionsAvailable(i, p) && i.adicionais.every(a => p.adicionais.some(v => v.id === a.id)); });
  function saveCart() {
    try {
      sessionStorage.setItem(`mf-cart-${token}-${draftId}`, JSON.stringify(cart));
      sessionStorage.setItem(noteKey(), byId('observacao-pedido').value);
    } catch { /* Armazenamento pode estar indisponível. */ }
  }
  const unit = item => (Math.round(Number(item.preco) * 100) + item.adicionais.reduce((sum, a) => sum + Math.round(Number(a.preco) * 100), 0)) / 100;
  const total = () => cart.reduce((sum, item) => sum + Math.round(unit(item) * 100) * item.quantidade, 0) / 100;
  const renderOrders = orders => MF.renderOrders(orders, {mesaPath, permitirPedido:true});
  function renderCart() {
    byId('cart-items').innerHTML = cart.length ? cart.map((item, i) => `<div class="cart-item"><div><strong>${escape(item.nome)}</strong><div class="cart-item-actions"><button class="text-link" data-edit="${i}" ${attempt ? 'disabled' : ''} aria-label="Editar ${escape(item.nome)}">Editar item</button><button class="remove-button" data-remove="${i}" ${attempt ? 'disabled' : ''} aria-label="Remover ${escape(item.nome)}">Remover</button></div></div><p class="small muted">${(item.opcoes || []).map(c => `${escape(c.grupo)}: ${escape(c.opcao)}`).concat(item.adicionais.map(a => escape(a.nome)), item.observacao ? [escape(item.observacao)] : []).join(' · ')}</p><div class="quantity-row"><div class="quantity-control"><button data-quantity="${i}" data-delta="-1" aria-label="Diminuir quantidade de ${escape(item.nome)}" ${attempt || item.quantidade <= 1 ? 'disabled' : ''}>−</button><span>${item.quantidade}</span><button data-quantity="${i}" data-delta="1" aria-label="Aumentar quantidade de ${escape(item.nome)}" ${attempt || item.quantidade >= 99 ? 'disabled' : ''}>+</button></div><strong>${money(unit(item) * item.quantidade)}</strong></div></div>`).join('') : `<div class="screen-empty"><span class="empty-symbol" aria-hidden="true">＋</span><h2>Seu carrinho está vazio</h2><p>Escolha algo no cardápio para começar seu pedido.</p><a class="btn btn-primary" href="${mesaPath}" data-client-link="cardapio">Explorar o cardápio</a></div>`;
    byId('cart-count').textContent = cart.reduce((sum, item) => sum + item.quantidade, 0);
    byId('cart-total').textContent = money(total());
    byId('revisar').disabled = !cart.length || !access || closing || !navigator.onLine || sending || ((!menuReady || !cartAvailable()) && !attempt);
    byId('cart-warning').hidden = !cart.length || cartAvailable();
    byId('cart-warning').textContent = 'Há itens ou escolhas que mudaram. Edite os itens sinalizados ou remova-os para continuar.';
    byId('pedido-destino').textContent = `${sessionId ? `Atendimento #${sessionId}` : 'Novo atendimento'} · Mesa ${document.querySelector('.table-tag strong').textContent}`;
    byId('cart-undo').hidden = !removedItem || Boolean(attempt);
    byId('revisar').textContent = sending ? 'Enviando…' : attempt ? 'Conferir envio pendente' : `Enviar pedido · ${money(total())}`;
    byId('revisar-help').textContent = closing ? 'Conta em fechamento. Peça à equipe para retomar o atendimento se quiser pedir mais.' : !access ? 'Inicie um novo atendimento para continuar.' : !navigator.onLine ? 'Reconecte para revisar e enviar o pedido.' : attempt ? 'Há um envio sem confirmação. Esta ação consulta os pedidos e repete somente a mesma tentativa, sem criar outro pedido.' : !cart.length ? 'Adicione um produto para continuar.' : !cartAvailable() ? 'Edite as escolhas que mudaram ou remova o item indisponível.' : 'Ao enviar, você confirma os itens e o total exibidos neste carrinho.';
    byId('nav-cart-count').textContent = byId('cart-count').textContent;
    byId('nav-cart-count').hidden = !cart.length;
    byId('cart-shortcut').hidden = !cart.length || currentView !== 'cardapio';
    byId('cart-shortcut-total').textContent = `${byId('cart-count').textContent} ${byId('cart-count').textContent === '1' ? 'item' : 'itens'} · ${money(total())}`;
  }
  const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  function renderProducts() {
    const visible = products.filter(p => (selected === null || p.categoria === selected) && normalize(`${p.nome} ${p.descricao}`).includes(normalize(search)));
    byId('menu-results').textContent = `${visible.length} produto${visible.length === 1 ? '' : 's'}`;
    byId('produtos').innerHTML = visible.map(p => `<article class="product-card ${p.disponivel ? '' : 'unavailable'}"><div class="product-image">${p.foto ? `<img src="${escape(p.foto)}" alt="${escape(p.nome)}" loading="lazy">` : `<span aria-hidden="true" class="food-placeholder">${escape(p.nome.charAt(0))}</span>`}${!p.disponivel ? '<span class="unavailable-tag">Indisponível</span>' : ''}</div><div class="product-body"><h3>${escape(p.nome)}</h3><p>${escape(p.descricao)}</p><div class="product-footer"><strong>${money(p.preco)}</strong><button type="button" class="add-button" data-product="${p.id}" ${!menuReady || !p.disponivel || !access || closing ? 'disabled' : ''} title="${!p.disponivel ? 'Produto indisponível' : closing ? 'Conta em fechamento' : !access ? 'Inicie um novo atendimento'  : 'Personalizar e adicionar ao carrinho'}" aria-label="Adicionar ${escape(p.nome)}">${p.disponivel ? 'Adicionar' : 'Indisponível'}</button></div></div></article>`).join('') || '<div class="menu-empty"><h3>Nenhum produto encontrado</h3><p>Tente outro nome ou consulte todas as categorias.</p><button type="button" class="btn btn-outline-primary" data-clear-menu>Limpar busca e filtros</button></div>';
  }
  function syncCartPrices() {
    if (sending || attempt) return;
    let changed = false;
    cart.forEach(item => {
      const product = products.find(p => p.id === item.produto_id);
      if (!product) return;
      if (item.preco !== product.preco) changed = true;
      item.preco = product.preco;
      if (item.opcoes_versao !== product.opcoes_versao) changed = true;
      item.opcoes_versao = product.opcoes_versao;
      item.opcoes = (item.opcoes || []).map(c => {
        const group = (product.grupos_opcoes || []).find(g => g.id === c.grupo_id);
        const option = group?.opcoes.find(o => o.id === c.opcao_id);
        return option ? {...c, grupo:group.nome, opcao:option.nome} : c;
      });
      item.adicionais = item.adicionais.map(a => {
        const current = product.adicionais.find(v => v.id === a.id);
        if (current && current.preco !== a.preco) changed = true;
        return current || a;
      });
    });
    if (changed) { saveCart(); feedback('O cardápio foi atualizado. Confira os preços e as escolhas no carrinho.'); }
    return changed;
  }
  async function loadMenu() {
    const categories = await api('/api/cardapio/');
    MF.connectionStatus('cardapio', true);
    const recovered = !menuReady;
    menuReady = true;
    const signature = JSON.stringify(categories);
    if (signature === menuSignature) { if (syncCartPrices() || recovered) { renderCart(); renderProducts(); } return; }
    menuSignature = signature;
    products = categories.flatMap(c => c.produtos);
    syncCartPrices();
    renderCart();
    byId('categorias').innerHTML = `<button data-category="" aria-pressed="${selected === null}" class="${selected === null ? 'active' : ''}">Todos</button>` + categories.map(c => `<button data-category="${c.id}" aria-pressed="${selected === c.id}" class="${selected === c.id ? 'active' : ''}">${escape(c.nome)}</button>`).join('');
    renderProducts();
    if (byId('produto-dialog').open && currentProduct) {
      const previous = currentProduct;
      currentProduct = products.find(p => p.id === currentProduct.id);
      byId('adicionar-item').disabled = !menuReady || !access || closing || !currentProduct?.disponivel;
      if (!currentProduct?.disponivel) feedback('Este produto ficou indisponível. Feche esta janela e escolha outro item.', true);
      else {
        if (JSON.stringify(previous.grupos_opcoes) !== JSON.stringify(currentProduct.grupos_opcoes)) {
          renderOptionGroups(); feedback('As escolhas deste produto mudaram. Selecione novamente antes de adicionar.', true);
        }
        byId('produto-preco').textContent = money(currentProduct.preco);
        updateProductTotal();
        if (previous.preco !== currentProduct.preco) feedback('O preço deste produto foi atualizado. Confira o total antes de adicionar.');
      }
    }
  }
  function refresh() {
    if (sending) return Promise.resolve();
    if (!refreshPromise) {
      const menu = loadMenu().catch(error => {
        MF.connectionStatus('cardapio', false);
        menuReady = false; renderCart(); renderProducts();
        feedback(`Cardápio indisponível. ${error.message}`, true);
      });
      // Conta e andamento continuam atualizando quando só o catálogo falha.
      refreshPromise = Promise.all([menu, refreshContext()]).finally(() => { refreshPromise = null; });
    }
    return refreshPromise;
  }
  async function refreshContext() {
    try {
    const mesa = await api(base);
    access = mesa.acesso_liberado;
    if (!access) { location.replace(mesaPath + '?bloqueado=1'); return; }
    if (!ended && mesa.atendimento_encerrado) feedback('Seu atendimento foi encerrado. Obrigado pela visita!');
    ended = mesa.atendimento_encerrado;
    byId('novo-atendimento').hidden = !ended;
    if (!loadedContext || mesa.atendimento_id !== draftId) {
      if (byId('produto-dialog').open) byId('produto-dialog').close();
      currentProduct = null; editingIndex = null;
      byId('resumo-conta').textContent = 'Carregando esta comanda…';
      byId('lista-pedidos').textContent = 'Carregando os pedidos desta comanda…';
      byId('conta-total').textContent = money(0);
      lastOrders = ''; lastBill = '';
      draftId = mesa.atendimento_id;
      attempt = null;
      cart = []; removedItem = null;
      byId('observacao-pedido').value = '';
      if (access) {
        try {
          attempt = JSON.parse(sessionStorage.getItem(attemptKey()) || 'null');
          // A chave de armazenamento já fixa o rascunho original do envio legado.
          if (attempt && !attempt.atendimento_id) { attempt.atendimento_id = draftId; saveAttempt(); }
          if (attempt && attempt.atendimento_id !== draftId) {
            attempt = null; saveAttempt();
            feedback('Atualizamos a confirmação de pedidos. Confira seus pedidos antes de enviar novamente.', true);
          }
          const stored = JSON.parse(sessionStorage.getItem(`mf-cart-${token}-${draftId}`) || '[]');
          if (Array.isArray(stored)) cart = stored.filter(i => i && Number.isInteger(i.quantidade) && i.quantidade > 0 && Array.isArray(i.adicionais));
          byId('observacao-pedido').value = sessionStorage.getItem(noteKey()) || '';
        } catch { cart = []; }
      }
      syncCartPrices(); renderCart(); renderProducts();
    }
    const previousSessionId = sessionId;
    sessionId = mesa.sessao_id;
    if (previousSessionId !== sessionId) renderCart();
    loadedContext = true;
    byId('session-label').textContent = sessionId ? `Atendimento #${sessionId}` : ended ? 'Comanda encerrada' : 'Peça sem chamar a equipe';
    byId('session-warning').hidden = true;
    byId('session-warning').querySelector('strong').textContent = ended ? 'Atendimento encerrado' : 'Mesa sem sessão aberta';
    byId('client-error').hidden = true;
    byId('pedir-conta').disabled = true;
    if (!sessionId) {
      closing = false; byId('fechamento-aviso').hidden = true;
      byId('lista-pedidos').innerHTML = '<p class="empty-state">Seus pedidos aparecerão aqui depois da confirmação.</p>';
      byId('resumo-conta').textContent = 'Escolha seus produtos. O atendimento será aberto ao confirmar o primeiro pedido.';
      byId('conta-total').textContent = money(0);
      byId('conta-quantidade').textContent = 'Nenhum pedido enviado.';
      byId('conta-status').textContent = ended ? 'Atendimento encerrado. Obrigado pela visita!' : 'O atendimento começa automaticamente no primeiro pedido.';
      byId('nav-orders-count').hidden = true;
      lastOrders = ''; lastBill = '';
      MF.connectionStatus('comanda', true);
      return;
    }
    const [orders, bill] = await Promise.all([api(privateUrl('pedidos/')), api(privateUrl('conta/'))]);
    if (bill.sessao_id !== sessionId || orders.some(p => p.sessao !== sessionId)) throw new Error('A comanda mudou. Atualize a página.');
    if (closing !== bill.conta_solicitada) { closing = bill.conta_solicitada; renderCart(); renderProducts(); }
    byId('fechamento-aviso').hidden = !closing;
    byId('session-label').textContent = closing ? `Comanda #${sessionId} · em fechamento` : `Atendimento #${sessionId}`;
    if (attempt && orders.some(p => p.chave_envio === attempt.chave_envio)) {
      attempt = null; saveAttempt(); cart = []; removedItem = null; byId('observacao-pedido').value = ''; saveCart(); renderCart();
      feedback('Pedido recebido pela cozinha.');
      showView('pedidos', true, true);
    }
    const signature = JSON.stringify(orders);
    if (signature !== lastOrders) {
      lastOrders = signature;
      byId('lista-pedidos').innerHTML = renderOrders(orders);
    }
    if (JSON.stringify(bill) !== lastBill) {
      lastBill = JSON.stringify(bill);
      byId('resumo-conta').innerHTML = bill.pedidos.length ? bill.pedidos.map(p => `<div class="bill-order"><div class="bill-row"><div><strong>Pedido #${p.id}</strong><p class="small muted mb-0">${statusNames[p.status]}${p.status === 'CANCELADO' ? ' · sem cobrança' : ''}</p></div><strong>${money(p.status === 'CANCELADO' ? 0 : p.valor_total)}</strong></div>${itemList(p)}</div>`).join('') : '<p class="empty-state">Ainda não há pedidos na sua comanda.</p>';
    }
    byId('nav-orders-count').textContent = orders.length;
    byId('nav-orders-count').hidden = !orders.length;
    byId('conta-total').textContent = money(bill.valor_total);
    byId('conta-quantidade').textContent = `${bill.pedidos.length} ${bill.pedidos.length === 1 ? 'pedido nesta comanda' : 'pedidos nesta comanda'}`;
    byId('conta-status').textContent = bill.conta_solicitada ? 'Conta em fechamento. Para pedir mais, solicite à equipe a retomada do atendimento.' : 'O pagamento é feito com a equipe do restaurante.';
    byId('pedir-conta').disabled = bill.conta_solicitada || !navigator.onLine;
    byId('pedir-conta').textContent = bill.conta_solicitada ? 'Fechamento solicitado ✓' : 'Solicitar fechamento';
    MF.connectionStatus('comanda', true);
    } catch (error) {
      MF.connectionStatus('comanda', false);
      byId('client-error-message').textContent = error.message;
      byId('client-error').hidden = false;
      throw error;
    }
  }
  document.addEventListener('click', event => {
    const button = event.target.closest('button');
    if (!button) return;
    if (button.hasAttribute('data-continue-menu')) { showView('cardapio', true, true); return; }
    if (button.hasAttribute('data-clear-menu')) {
      selected = null; search = ''; byId('buscar-produto').value = '';
      document.querySelectorAll('[data-category]').forEach(b => { b.classList.toggle('active', b.dataset.category === ''); b.setAttribute('aria-pressed', String(b.dataset.category === '')); });
      renderProducts();
    }
    if (attempt && (button.dataset.product || button.dataset.edit !== undefined || button.dataset.remove !== undefined || button.dataset.quantity !== undefined)) { feedback('Há um envio aguardando confirmação. Confira seus pedidos e tente confirmar antes de alterar o carrinho.', true); return; }
    if (button.hasAttribute('data-category')) {
      selected = button.dataset.category ? Number(button.dataset.category) : null;
      document.querySelectorAll('[data-category]').forEach(b => { b.classList.toggle('active', b === button); b.setAttribute('aria-pressed', String(b === button)); });
      renderProducts();
    }
    if (button.dataset.product) openProduct(Number(button.dataset.product));
    if (button.dataset.edit !== undefined) {
      const index = Number(button.dataset.edit);
      openProduct(cart[index].produto_id, index);
    }
    if (button.dataset.remove !== undefined) {
      const index = Number(button.dataset.remove);
      removedItem = {item:cart[index], index, draftId};
      cart.splice(index,1); saveCart(); renderCart();
      byId('cart-undo-message').textContent = `${removedItem.item.nome} removido.`;
      byId('desfazer-remocao').focus({preventScroll:true});
    }
    if (button.dataset.quantity !== undefined) {
      const item = cart[Number(button.dataset.quantity)];
      item.quantidade = Math.min(99, Math.max(1,item.quantidade + Number(button.dataset.delta)));
      saveCart(); renderCart();
      byId('cart-items').querySelector(`[data-quantity="${button.dataset.quantity}"][data-delta="${button.dataset.delta}"]`)?.focus({preventScroll:true});
    }
  });
  byId('desfazer-remocao').addEventListener('click', () => {
    if (!removedItem || removedItem.draftId !== draftId || attempt) return;
    cart.splice(Math.min(removedItem.index, cart.length), 0, removedItem.item);
    removedItem = null; saveCart(); renderCart();
    feedback('Item devolvido ao carrinho.');
  });
  function renderOptionGroups(choices = []) {
    byId('produto-opcoes').innerHTML = (currentProduct.grupos_opcoes || []).map(g => `<fieldset class="drink-options"><legend>${escape(g.nome)}</legend><p>Escolha 1 · ${g.obrigatorio ? 'obrigatório' : 'opcional'} · sem acréscimo</p><div class="drink-options-list">${g.opcoes.map(o => `<label><input type="radio" name="opcao-${g.id}" data-option-group="${g.id}" value="${o.id}" ${g.obrigatorio ? 'required' : ''} ${choices.some(c => c.grupo_id === g.id && c.opcao_id === o.id) ? 'checked' : ''}> ${escape(o.nome)}</label>`).join('')}${!g.obrigatorio ? `<label><input type="radio" name="opcao-${g.id}" value="" ${!choices.some(c => c.grupo_id === g.id) ? 'checked' : ''}> Sem preferência</label>` : ''}</div></fieldset>`).join('');
  }
  function openProduct(id, index = null) {
    currentProduct = products.find(p => p.id === id);
    if (!currentProduct?.disponivel || !menuReady || closing || !access) { feedback('Este produto está indisponível. Remova-o do carrinho ou escolha outro.', true); return; }
    editingIndex = index;
    const item = index === null ? null : cart[index];
    byId('produto-titulo').textContent = currentProduct.nome;
    byId('produto-descricao').textContent = currentProduct.descricao;
    byId('produto-quantidade').value = item?.quantidade || 1;
    byId('produto-observacao').value = item?.observacao || '';
    renderOptionGroups(item?.opcoes || []);
    byId('produto-preco').textContent = money(currentProduct.preco);
    byId('adicionar-item').disabled = false;
    byId('adicionar-item').textContent = item ? 'Salvar item no carrinho' : 'Adicionar ao carrinho';
    byId('produto-adicionais').innerHTML = currentProduct.adicionais.length ? '<h3 class="small-heading">Adicionais · opcionais</h3>' + currentProduct.adicionais.map(a => `<label class="extra-option"><span><input type="checkbox" name="adicional" value="${a.id}" ${item?.adicionais.some(c => c.id === a.id) ? 'checked' : ''}> ${escape(a.nome)}</span><strong>+ ${money(a.preco)}</strong></label>`).join('') : '';
    MF.openDialog(byId('produto-dialog'));
    updateProductTotal();
  }
  function updateProductTotal() {
    if (!currentProduct) return;
    const ids = [...byId('produto-adicionais').querySelectorAll('input:checked')].map(n => Number(n.value));
    byId('produto-total').textContent = money(unit({preco:currentProduct.preco, adicionais:currentProduct.adicionais.filter(a => ids.includes(a.id))}) * Number(byId('produto-quantidade').value || 0));
  }
  byId('produto-form').addEventListener('input', updateProductTotal);
  byId('observacao-pedido').addEventListener('input', saveCart);
  byId('buscar-produto').addEventListener('input', event => { search = event.target.value.trim(); renderProducts(); });
  byId('tentar-novamente').addEventListener('click', () => refresh().catch(e => feedback(e.message, true)));
  byId('produto-form').addEventListener('submit', event => {
    event.preventDefault();
    currentProduct = products.find(p => p.id === currentProduct?.id);
    if (!menuReady || !access || closing || !currentProduct?.disponivel || attempt) { feedback('Este item não pode ser adicionado agora.', true); return; }
    const ids = [...document.querySelectorAll('[name="adicional"]:checked')].map(n => Number(n.value));
    const opcoes = [...byId('produto-opcoes').querySelectorAll('[data-option-group]:checked')].map(input => {
      const group = currentProduct.grupos_opcoes.find(g => g.id === input.dataset.optionGroup);
      const option = group?.opcoes.find(o => o.id === input.value);
      return option ? {grupo_id:group.id, grupo:group.nome, opcao_id:option.id, opcao:option.nome} : null;
    }).filter(Boolean);
    const item = {produto_id:currentProduct.id, nome:currentProduct.nome, preco:currentProduct.preco, quantidade:Number(byId('produto-quantidade').value), adicionais:currentProduct.adicionais.filter(a => ids.includes(a.id)), observacao:byId('produto-observacao').value.trim(), opcoes, opcoes_versao:currentProduct.opcoes_versao};
    if (!optionsAvailable(item, currentProduct) || !byId('produto-form').reportValidity()) { feedback('Escolha as opções obrigatórias deste produto.', true); return; }
    if (editingIndex === null) cart.push(item); else cart[editingIndex] = item;
    const edited = editingIndex !== null;
    saveCart(); renderCart(); byId('produto-dialog').close();
    feedback(edited ? 'Item atualizado no carrinho.' : 'Adicionado ao carrinho. Você pode editar antes de enviar.');
  });
  byId('revisar').addEventListener('click', async () => {
    if (sending || !cart.length) return;
    // Compare com o que estava visível no clique, antes de qualquer atualização remota.
    const seen = cartSignature();
    try { await refresh(); } catch (error) { feedback(error.message, true); return; }
    if (sending || !cart.length) return;
    if (!access || closing || ((!menuReady || !cartAvailable()) && !attempt)) return;
    if (!attempt && seen !== cartSignature()) { feedback('O carrinho, os preços ou a comanda mudaram. Confira o total atualizado e toque em Enviar pedido novamente.', true); return; }
    sending = true; renderCart();
    try {
      if (!attempt) {
        attempt = {chave_envio:MF.uuid(), mesa_uuid:token, atendimento_id:draftId, sessao_id:sessionId, total_esperado:total().toFixed(2), observacao:byId('observacao-pedido').value, itens:cart.map(i => ({produto_id:i.produto_id, quantidade:i.quantidade, observacao:i.observacao, adicionais_ids:i.adicionais.map(a => a.id), ...((i.opcoes || []).length ? {opcoes:i.opcoes.map(c => ({grupo_id:c.grupo_id, opcao_id:c.opcao_id}))} : {}), ...(i.opcoes_versao ? {opcoes_versao:i.opcoes_versao} : {})}))};
        saveAttempt();
      }
      const sent = await api('/api/pedidos/criar/', {method:'POST', body:JSON.stringify(attempt)});
      attempt = null; saveAttempt(); removedItem = null;
      cart = []; byId('observacao-pedido').value = ''; saveCart();
      feedback(`Pedido #${sent.id} enviado! Acompanhe o preparo por aqui.`);
      showView('pedidos', true, true);
    } catch (error) {
      if (error.status && error.status < 500) { attempt = null; saveAttempt(); }
      feedback(`${error.message} Confira os pedidos antes de tentar novamente.`, true);
      await loadMenu().catch(() => {});
    } finally { sending = false; renderCart(); refresh().catch(e => feedback(e.message, true)); }
  });
  async function iniciarAtendimento() {
    byId('iniciar-atendimento').disabled = true;
    try {
      await api(`${base}novo-atendimento/`, {method:'POST'});
      loadedContext = false;
      await refresh(); showView('cardapio', true, true);
    } catch (error) { feedback(error.message, true); }
    finally { byId('iniciar-atendimento').disabled = false; }
  }
  byId('iniciar-atendimento').addEventListener('click', iniciarAtendimento);
  byId('pedir-conta').addEventListener('click', async () => {
    byId('pedir-conta').disabled = true;
    try { await api(privateUrl('solicitar-conta/'), {method:'POST'}); feedback('Conta solicitada. O garçom vem ajudar você.'); await refresh(); }
    catch (error) { feedback(error.message,true); byId('pedir-conta').disabled = false; }
  });
  let lastActivity = 0;
  function activity() {
    if (!access || !draftId || sessionId || sending || !navigator.onLine || Date.now() - lastActivity < 30000) return;
    lastActivity = Date.now();
    api(privateUrl('atividade/'), {method:'POST'}).catch(() => refreshContext().catch(() => {}));
  }
  ['pointerdown','keydown','input'].forEach(type => document.addEventListener(type, activity, {passive:true}));
  window.addEventListener('offline', renderCart);
  window.addEventListener('online', () => { renderCart(); refresh().catch(e => feedback(e.message,true)); });
  document.documentElement.style.scrollBehavior = 'auto';
  const legacyView = location.hash.slice(1);
  if (Object.hasOwn(views, legacyView)) {
    history.replaceState(null, '', views[legacyView].path);
    showView(legacyView);
  } else showView(currentView);
  poll(refresh);
})();
