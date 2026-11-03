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
  let draftId = null, access = false, loadedContext = false, closing = false, ended = false, menuSignature = '', reviewSignature = '';
  let menuReady = false, refreshPromise = null;
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
  const cartAvailable = () => cart.every(i => { const p = products.find(p => p.id === i.produto_id); return p?.disponivel && i.adicionais.every(a => p.adicionais.some(v => v.id === a.id)); });
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
    byId('cart-items').innerHTML = cart.length ? cart.map((item, i) => `<div class="cart-item"><div><strong>${escape(item.nome)}</strong><button class="remove-button" data-remove="${i}" aria-label="Remover ${escape(item.nome)}">Remover</button></div><p class="small muted">${item.adicionais.map(a => escape(a.nome)).join(', ')}${item.observacao ? ` · ${escape(item.observacao)}` : ''}</p><div class="quantity-row"><div class="quantity-control"><button data-quantity="${i}" data-delta="-1" aria-label="Diminuir quantidade de ${escape(item.nome)}" ${item.quantidade <= 1 ? 'disabled' : ''}>−</button><span>${item.quantidade}</span><button data-quantity="${i}" data-delta="1" aria-label="Aumentar quantidade de ${escape(item.nome)}" ${item.quantidade >= 99 ? 'disabled' : ''}>+</button></div><strong>${money(unit(item) * item.quantidade)}</strong></div></div>`).join('') : `<div class="screen-empty"><span class="empty-symbol" aria-hidden="true">＋</span><h2>Seu carrinho está vazio</h2><p>Escolha algo no cardápio para começar seu pedido.</p><a class="btn btn-primary" href="${mesaPath}" data-client-link="cardapio">Explorar o cardápio</a></div>`;
    byId('cart-count').textContent = cart.reduce((sum, item) => sum + item.quantidade, 0);
    byId('cart-total').textContent = money(total());
    byId('revisar').disabled = !cart.length || !access || closing || !navigator.onLine || sending || ((!menuReady || !cartAvailable()) && !attempt);
    byId('cart-warning').hidden = !cart.length || cartAvailable();
    byId('revisar-help').textContent = closing ? 'Conta em fechamento. Peça à equipe para retomar o atendimento se quiser pedir mais.' : !access ? 'Inicie um novo atendimento para continuar.' : !navigator.onLine ? 'Reconecte para revisar e enviar o pedido.' : attempt ? 'Aguardando confirmação de um envio. Confira seus pedidos antes de tentar novamente.' : !cart.length ? 'Adicione um produto para continuar.' : !cartAvailable() ? 'Remova os itens indisponíveis para continuar.' : 'Você ainda vai conferir os itens antes de enviar à cozinha.';
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
      item.adicionais = item.adicionais.map(a => {
        const current = product.adicionais.find(v => v.id === a.id);
        if (current && current.preco !== a.preco) changed = true;
        return current || a;
      });
    });
    if (changed) { saveCart(); feedback('Os preços do cardápio foram atualizados. Revise seu carrinho.'); }
    return changed;
  }
  async function loadMenu() {
    const categories = await api('/api/cardapio/');
    const recovered = !menuReady;
    menuReady = true;
    const signature = JSON.stringify(categories);
    if (signature === menuSignature) { if (syncCartPrices() || recovered) { renderCart(); renderProducts(); } return; }
    menuSignature = signature;
    products = categories.flatMap(c => c.produtos);
    syncCartPrices();
    renderCart();
    byId('categorias').innerHTML = `<button data-category="" class="${selected === null ? 'active' : ''}">Todos</button>` + categories.map(c => `<button data-category="${c.id}" class="${selected === c.id ? 'active' : ''}">${escape(c.nome)}</button>`).join('');
    renderProducts();
    if (byId('produto-dialog').open && currentProduct) {
      const previous = currentProduct;
      currentProduct = products.find(p => p.id === currentProduct.id);
      byId('adicionar-item').disabled = !menuReady || !access || closing || !currentProduct?.disponivel;
      if (!currentProduct?.disponivel) feedback('Este produto ficou indisponível. Feche esta janela e escolha outro item.', true);
      else {
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
    if (!ended && mesa.atendimento_encerrado) feedback('Seu atendimento foi encerrado. Obrigado pela visita!');
    ended = mesa.atendimento_encerrado;
    byId('novo-atendimento').hidden = !ended;
    if (!loadedContext || mesa.atendimento_id !== draftId) {
      byId('resumo-conta').textContent = 'Carregando esta comanda…';
      byId('lista-pedidos').textContent = 'Carregando os pedidos desta comanda…';
      byId('conta-total').textContent = money(0);
      lastOrders = ''; lastBill = '';
      if (byId('compartilhar-dialog').open) byId('compartilhar-dialog').close();
      draftId = mesa.atendimento_id;
      attempt = null;
      cart = [];
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
    sessionId = mesa.sessao_id;
    byId('comanda-label').textContent = sessionId ? `Comanda #${sessionId} · Mesa ${document.querySelector('.table-tag strong').textContent}` : ended ? 'Sua comanda foi encerrada' : 'Seu pedido em conta separada';
    byId('compartilhar-comanda').disabled = !sessionId || !access;
    byId('compartilhar-comanda').title = sessionId ? 'Convidar sua família para esta comanda' : 'Envie o primeiro pedido para compartilhar';
    byId('separar-comanda').hidden = !sessionId;
    const ownTabs = mesa.comandas || [];
    byId('minhas-comandas-label').hidden = ownTabs.length < 2 && !(ownTabs.length && !sessionId);
    const tabsSignature = JSON.stringify([sessionId, ownTabs]);
    if (byId('minhas-comandas').dataset.signature !== tabsSignature) {
      byId('minhas-comandas').innerHTML = (!sessionId ? '<option value="">Novo pedido separado</option>' : '') + ownTabs.map(tab => `<option value="${tab.id}">Comanda #${tab.id}${tab.conta_solicitada ? ' · em fechamento' : ''}</option>`).join('');
      byId('minhas-comandas').value = sessionId || '';
      byId('minhas-comandas').dataset.signature = tabsSignature;
    }
    loadedContext = true;
    byId('session-label').textContent = sessionId ? 'Sessão aberta' : ended ? 'Sessão encerrada' : 'Pronta para seu pedido';
    byId('session-warning').hidden = true;
    byId('session-warning').querySelector('strong').textContent = ended ? 'Atendimento encerrado' : 'Mesa sem sessão aberta';
    byId('client-error').hidden = true;
    byId('pedir-conta').disabled = true;
    if (!sessionId) {
      closing = false; byId('fechamento-aviso').hidden = true;
      byId('lista-pedidos').innerHTML = '<p class="empty-state">Seus pedidos aparecerão aqui depois da confirmação.</p>';
      byId('resumo-conta').textContent = 'Escolha seus produtos. O atendimento será aberto ao confirmar o primeiro pedido.';
      byId('conta-total').textContent = money(0);
      byId('conta-quantidade').textContent = 'Nenhuma sessão aberta.';
      byId('conta-status').textContent = ended ? 'Atendimento encerrado. Obrigado pela visita!' : 'O atendimento começa automaticamente no primeiro pedido.';
      byId('nav-orders-count').hidden = true;
      lastOrders = ''; lastBill = '';
      return;
    }
    const [orders, bill] = await Promise.all([api(privateUrl('pedidos/')), api(privateUrl('conta/'))]);
    if (bill.sessao_id !== sessionId || orders.some(p => p.sessao !== sessionId)) throw new Error('A comanda mudou. Atualize a página.');
    if (closing !== bill.conta_solicitada) { closing = bill.conta_solicitada; renderCart(); renderProducts(); }
    byId('fechamento-aviso').hidden = !closing;
    byId('session-label').textContent = closing ? 'Em fechamento' : 'Sessão aberta';
    if (attempt && orders.some(p => p.chave_envio === attempt.chave_envio)) {
      attempt = null; saveAttempt(); cart = []; byId('observacao-pedido').value = ''; saveCart(); renderCart();
      byId('revisao-dialog').close(); feedback('Pedido recebido pela cozinha.');
      showView('pedidos', true, true);
    }
    const signature = JSON.stringify(orders);
    if (signature !== lastOrders) {
      lastOrders = signature;
      byId('lista-pedidos').innerHTML = renderOrders(orders);
    }
    if (JSON.stringify(bill) !== lastBill) {
      lastBill = JSON.stringify(bill);
      byId('resumo-conta').innerHTML = bill.pedidos.length ? bill.pedidos.map(p => `<div class="bill-order"><div class="bill-row"><div><strong>Pedido #${p.id}</strong><p class="small muted mb-0">${statusNames[p.status]}${p.status === 'CANCELADO' ? ' · sem cobrança' : ''}</p></div><strong>${money(p.status === 'CANCELADO' ? 0 : p.valor_total)}</strong></div>${itemList(p)}</div>`).join('') : '<p class="empty-state">Ainda não há pedidos na conta desta mesa.</p>';
    }
    byId('nav-orders-count').textContent = orders.length;
    byId('nav-orders-count').hidden = !orders.length;
    byId('conta-total').textContent = money(bill.valor_total);
    byId('conta-quantidade').textContent = `${bill.pedidos.length} ${bill.pedidos.length === 1 ? 'pedido nesta sessão' : 'pedidos nesta sessão'}`;
    byId('conta-status').textContent = bill.conta_solicitada ? 'Conta em fechamento. Para pedir mais, solicite à equipe a retomada do atendimento.' : 'O pagamento é feito com a equipe do restaurante.';
    byId('pedir-conta').disabled = bill.conta_solicitada || !navigator.onLine;
    byId('pedir-conta').textContent = bill.conta_solicitada ? 'Conta solicitada ✓' : 'Pedir a conta';
    } catch (error) {
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
      document.querySelectorAll('[data-category]').forEach(b => b.classList.toggle('active', b.dataset.category === ''));
      renderProducts();
    }
    if (attempt && (button.dataset.product || button.dataset.remove !== undefined || button.dataset.quantity !== undefined)) { feedback('Há um envio aguardando confirmação. Revise e tente novamente antes de alterar o carrinho.', true); return; }
    if (button.hasAttribute('data-category')) {
      selected = button.dataset.category ? Number(button.dataset.category) : null;
      document.querySelectorAll('[data-category]').forEach(b => b.classList.toggle('active', b === button));
      renderProducts();
    }
    if (button.dataset.product) {
      currentProduct = products.find(p => p.id === Number(button.dataset.product));
      byId('produto-titulo').textContent = currentProduct.nome;
      byId('produto-descricao').textContent = currentProduct.descricao;
      byId('produto-quantidade').value = '1'; byId('produto-observacao').value = '';
      const soda = currentProduct.nome.trim().toLocaleLowerCase('pt-BR') === 'refrigerante lata';
      byId('produto-opcoes').hidden = !soda;
      document.querySelectorAll('input[name="sabor"]').forEach(input => { input.checked = false; input.required = soda; });
      byId('produto-observacao').maxLength = soda ? 230 : 255;
      byId('produto-preco').textContent = money(currentProduct.preco);
      byId('adicionar-item').disabled = false;
      byId('produto-adicionais').innerHTML = currentProduct.adicionais.length ? '<h3 class="small-heading">Deixe do seu jeito</h3>' + currentProduct.adicionais.map(a => `<label class="extra-option"><span><input type="checkbox" name="adicional" value="${a.id}"> ${escape(a.nome)}</span><strong>+ ${money(a.preco)}</strong></label>`).join('') : '';
      byId('produto-dialog').showModal();
      updateProductTotal();
    }
    if (button.dataset.remove !== undefined) { cart.splice(Number(button.dataset.remove),1); saveCart(); renderCart(); }
    if (button.dataset.quantity !== undefined) {
      const item = cart[Number(button.dataset.quantity)];
      item.quantidade = Math.min(99, Math.max(1,item.quantidade + Number(button.dataset.delta)));
      saveCart(); renderCart();
    }
  });
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
    const sabor = document.querySelector('input[name="sabor"]:checked')?.value;
    const observacao = [sabor ? `Sabor: ${sabor}` : '', byId('produto-observacao').value.trim()].filter(Boolean).join(' · ');
    cart.push({produto_id: currentProduct.id, nome: currentProduct.nome, preco: currentProduct.preco, quantidade: Number(byId('produto-quantidade').value), adicionais: currentProduct.adicionais.filter(a => ids.includes(a.id)), observacao});
    saveCart(); renderCart(); byId('produto-dialog').close(); feedback('Adicionado ao carrinho.');
  });
  function renderReview() {
    byId('revisao-itens').innerHTML = cart.map(i => `<div class="bill-row"><div><strong>${i.quantidade}× ${escape(i.nome)}</strong><p class="small muted mb-0">${i.adicionais.map(a => escape(a.nome)).join(', ')} ${escape(i.observacao)}</p></div><strong>${money(unit(i)*i.quantidade)}</strong></div>`).join('') + `<p class="small muted">${escape(byId('observacao-pedido').value)}</p>`;
    byId('revisao-total').textContent = money(total());
    reviewSignature = cartSignature();
    if (!byId('revisao-dialog').open) byId('revisao-dialog').showModal();
  }
  byId('revisar').addEventListener('click', async () => {
    try { await refresh(); } catch (error) { feedback(error.message, true); return; }
    if (sending) return;
    if (!access || closing || !cart.length || ((!menuReady || !cartAvailable()) && !attempt)) return;
    renderReview();
  });
  byId('confirmar').addEventListener('click', async () => {
    if (sending || !cart.length) return;
    try { await refresh(); } catch (error) { feedback(error.message, true); return; }
    if (sending) return;
    if (!access || closing || !cart.length || ((!menuReady || !cartAvailable()) && !attempt)) return;
    if (!attempt && cartSignature() !== reviewSignature) { renderReview(); feedback('O carrinho ou os preços mudaram. Confira o novo total e confirme novamente.', true); return; }
    sending = true; byId('confirmar').disabled = true; byId('confirmar').textContent = 'Enviando…';
    try {
      if (!attempt) {
        attempt = {chave_envio:MF.uuid(), mesa_uuid:token, atendimento_id:draftId, sessao_id:sessionId, total_esperado:total().toFixed(2), observacao:byId('observacao-pedido').value, itens:cart.map(i => ({produto_id:i.produto_id, quantidade:i.quantidade, observacao:i.observacao, adicionais_ids:i.adicionais.map(a => a.id)}))};
        saveAttempt();
      }
      await api('/api/pedidos/criar/', {method:'POST', body:JSON.stringify(attempt)});
      attempt = null; saveAttempt();
      cart = []; byId('observacao-pedido').value = ''; saveCart(); byId('revisao-dialog').close();
      feedback('Pedido enviado! A cozinha já recebeu.'); await refresh();
      showView('pedidos', true, true);
    } catch (error) { if (error.status && error.status < 500) { attempt = null; saveAttempt(); } feedback(`${error.message} Confira os pedidos antes de tentar novamente.`, true); await loadMenu().catch(() => {}); }
    finally { sending = false; byId('confirmar').disabled = false; byId('confirmar').textContent = 'Confirmar e enviar pedido →'; renderCart(); refresh().catch(e => feedback(e.message, true)); }
  });
  async function iniciarSeparado() {
    byId('iniciar-atendimento').disabled = true;
    try {
      await api(`${base}novo-atendimento/`, {method:'POST'});
      loadedContext = false;
      await refresh(); showView('cardapio', true, true);
    } catch (error) { feedback(error.message, true); }
    finally { byId('iniciar-atendimento').disabled = false; }
  }
  byId('iniciar-atendimento').addEventListener('click', iniciarSeparado);
  byId('separar-comanda').addEventListener('click', iniciarSeparado);
  byId('minhas-comandas').addEventListener('change', async event => {
    if (!event.target.value) return;
    try {
      await api(`${base}selecionar-comanda/`, {method:'POST', body:JSON.stringify({comanda_id:Number(event.target.value)})});
      loadedContext = false; await refresh();
    } catch (error) { feedback(error.message, true); }
  });
  byId('compartilhar-comanda').addEventListener('click', async () => {
    byId('compartilhar-comanda').disabled = true;
    try {
      const invite = await api(privateUrl('compartilhar/'), {method:'POST'});
      byId('compartilhar-link').value = invite.url;
      byId('compartilhar-qr').src = invite.qr_url;
      byId('compartilhar-validade').textContent = `Convite válido até ${new Date(invite.expira_em).toLocaleTimeString('pt-BR', {hour:'2-digit', minute:'2-digit', timeZone:'America/Sao_Paulo'})}. Após o pagamento ele deixa de funcionar.`;
      byId('enviar-convite').hidden = !navigator.share;
      byId('compartilhar-dialog').showModal();
    } catch (error) { feedback(error.message, true); }
    finally { byId('compartilhar-comanda').disabled = !sessionId || !access; }
  });
  byId('copiar-convite').addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(byId('compartilhar-link').value); feedback('Link copiado. Envie somente à sua família.'); }
    catch { byId('compartilhar-link').select(); feedback('Selecione e copie o link para enviar à sua família.'); }
  });
  byId('enviar-convite').addEventListener('click', async () => {
    try { await navigator.share({title:'Nossa comanda · MesaFácil', text:'Entre na nossa comanda para pedir junto.', url:byId('compartilhar-link').value}); }
    catch (error) { if (error.name !== 'AbortError') feedback('Não foi possível compartilhar. Copie o link.', true); }
  });
  byId('pedir-conta').addEventListener('click', async () => {
    byId('pedir-conta').disabled = true;
    try { await api(privateUrl('solicitar-conta/'), {method:'POST'}); feedback('Conta solicitada. O garçom vem ajudar você.'); await refresh(); }
    catch (error) { feedback(error.message,true); byId('pedir-conta').disabled = false; }
  });
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
