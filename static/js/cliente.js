'use strict';
(() => {
  const {money, escape, api, feedback, poll, statusNames, itemList} = MF;
  const token = document.body.dataset.mesa;
  const base = `/api/mesa/${token}/`;
  const byId = id => document.getElementById(id);
  let products = [], cart = [], sessionId = null, currentProduct = null, sending = false, selected = null, search = '';
  let ended = false, menuSignature = '', reviewSignature = '', cartInView = false;
  const cartSignature = () => JSON.stringify([sessionId, cart, byId('observacao-pedido').value]);
  let lastOrders = '', lastBill = '', refreshing = false, attempt = null;
  const attemptKey = () => `mf-attempt-${token}-${sessionId}`;
  function saveAttempt() { try { if (attempt) sessionStorage.setItem(attemptKey(), JSON.stringify(attempt)); else sessionStorage.removeItem(attemptKey()); } catch {} }
  const cartAvailable = () => cart.every(i => { const p = products.find(p => p.id === i.produto_id); return p?.disponivel && i.adicionais.every(a => p.adicionais.some(v => v.id === a.id)); });
  function saveCart() {
    try { sessionStorage.setItem(`mf-cart-${token}-${sessionId}`, JSON.stringify(cart)); } catch { /* Armazenamento pode estar indisponível. */ }
  }
  const unit = item => (Math.round(Number(item.preco) * 100) + item.adicionais.reduce((sum, a) => sum + Math.round(Number(a.preco) * 100), 0)) / 100;
  const total = () => cart.reduce((sum, item) => sum + Math.round(unit(item) * 100) * item.quantidade, 0) / 100;
  function renderCart() {
    byId('cart-items').innerHTML = cart.length ? cart.map((item, i) => `<div class="cart-item"><div><strong>${escape(item.nome)}</strong><button class="remove-button" data-remove="${i}" aria-label="Remover ${escape(item.nome)}">Remover</button></div><p class="small muted">${item.adicionais.map(a => escape(a.nome)).join(', ')}${item.observacao ? ` · ${escape(item.observacao)}` : ''}</p><div class="quantity-row"><div class="quantity-control"><button data-quantity="${i}" data-delta="-1" aria-label="Diminuir quantidade de ${escape(item.nome)}" ${item.quantidade <= 1 ? 'disabled' : ''}>−</button><span>${item.quantidade}</span><button data-quantity="${i}" data-delta="1" aria-label="Aumentar quantidade de ${escape(item.nome)}" ${item.quantidade >= 99 ? 'disabled' : ''}>+</button></div><strong>${money(unit(item) * item.quantidade)}</strong></div></div>`).join('') : '<p class="empty-state">Seu carrinho está vazio.<br>Use “Adicionar” em um produto.</p>';
    byId('cart-count').textContent = cart.reduce((sum, item) => sum + item.quantidade, 0);
    byId('cart-total').textContent = money(total());
    byId('revisar').disabled = !cart.length || !sessionId || !navigator.onLine || sending || (!cartAvailable() && !attempt);
    byId('cart-warning').hidden = !cart.length || cartAvailable();
    byId('revisar-help').textContent = !sessionId ? 'A mesa precisa estar aberta pelo garçom para receber pedidos.' : !navigator.onLine ? 'Reconecte para revisar e enviar o pedido.' : attempt ? 'Aguardando confirmação de um envio. Confira seus pedidos antes de tentar novamente.' : !cart.length ? 'Adicione um produto para continuar.' : !cartAvailable() ? 'Remova os itens indisponíveis para continuar.' : 'Você ainda vai conferir os itens antes de enviar à cozinha.';
    byId('cart-shortcut').hidden = !cart.length || cartInView;
    byId('cart-shortcut-total').textContent = `${byId('cart-count').textContent} item(ns) · ${money(total())}`;
  }
  const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  function renderProducts() {
    const visible = products.filter(p => (selected === null || p.categoria === selected) && normalize(`${p.nome} ${p.descricao}`).includes(normalize(search)));
    byId('menu-results').textContent = `${visible.length} produto${visible.length === 1 ? '' : 's'}`;
    byId('produtos').innerHTML = visible.map(p => `<article class="product-card ${p.disponivel ? '' : 'unavailable'}"><div class="product-image">${p.foto ? `<img src="${escape(p.foto)}" alt="${escape(p.nome)}" loading="lazy">` : `<span aria-hidden="true" class="food-placeholder">${escape(p.nome.charAt(0))}</span>`}${!p.disponivel ? '<span class="unavailable-tag">Indisponível</span>' : ''}</div><div class="product-body"><h3>${escape(p.nome)}</h3><p>${escape(p.descricao)}</p><div class="product-footer"><strong>${money(p.preco)}</strong><button type="button" class="add-button" data-product="${p.id}" ${!p.disponivel || !sessionId ? 'disabled' : ''} title="${!p.disponivel ? 'Produto indisponível' : !sessionId ? 'Aguarde o garçom abrir a mesa' : 'Personalizar e adicionar ao carrinho'}" aria-label="Adicionar ${escape(p.nome)}">${p.disponivel ? 'Adicionar' : 'Indisponível'}</button></div></div></article>`).join('') || '<div class="menu-empty"><h3>Nenhum produto encontrado</h3><p>Tente outro nome ou consulte todas as categorias.</p><button type="button" class="btn btn-outline-primary" data-clear-menu>Limpar busca e filtros</button></div>';
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
    const signature = JSON.stringify(categories);
    if (signature === menuSignature) { if (syncCartPrices()) renderCart(); return; }
    menuSignature = signature;
    products = categories.flatMap(c => c.produtos);
    syncCartPrices();
    renderCart();
    byId('categorias').innerHTML = `<button data-category="" class="${selected === null ? 'active' : ''}">Todos</button>` + categories.map(c => `<button data-category="${c.id}" class="${selected === c.id ? 'active' : ''}">${escape(c.nome)}</button>`).join('');
    renderProducts();
    if (byId('produto-dialog').open && currentProduct) {
      const previous = currentProduct;
      currentProduct = products.find(p => p.id === currentProduct.id);
      byId('adicionar-item').disabled = !sessionId || !currentProduct?.disponivel;
      if (!currentProduct?.disponivel) feedback('Este produto ficou indisponível. Feche esta janela e escolha outro item.', true);
      else {
        byId('produto-preco').textContent = money(currentProduct.preco);
        updateProductTotal();
        if (previous.preco !== currentProduct.preco) feedback('O preço deste produto foi atualizado. Confira o total antes de adicionar.');
      }
    }
  }
  async function refresh() {
    if (refreshing || sending) return;
    refreshing = true;
    try {
    await loadMenu();
    const mesa = await api(base);
    if (mesa.sessao_id !== sessionId) {
      if (sessionId && !mesa.sessao_id) { ended = true; feedback('Sua sessão foi encerrada. Obrigado pela visita!'); }
      if (mesa.sessao_id) ended = false;
      sessionId = mesa.sessao_id;
      attempt = null;
      try { attempt = JSON.parse(sessionStorage.getItem(attemptKey()) || 'null'); } catch {}
      cart = [];
      try {
        const stored = JSON.parse(sessionStorage.getItem(`mf-cart-${token}-${sessionId}`) || '[]');
        if (Array.isArray(stored)) cart = stored.filter(i => i && Number.isInteger(i.quantidade) && i.quantidade > 0 && Array.isArray(i.adicionais));
      } catch { cart = []; }
      syncCartPrices();
      renderCart();
      renderProducts();
    }
    byId('session-label').textContent = sessionId ? 'Sessão aberta' : ended ? 'Sessão encerrada' : 'Aguardando abertura';
    byId('session-warning').hidden = Boolean(sessionId);
    byId('session-warning').querySelector('strong').textContent = ended ? 'Atendimento encerrado' : 'Mesa sem sessão aberta';
    byId('session-message').textContent = ended ? 'Sua sessão foi encerrada. Obrigado pela visita! Para fazer outro pedido, peça a abertura de uma nova sessão.' : 'Você pode consultar o cardápio. Para adicionar produtos e enviar pedidos, peça ao garçom para abrir esta mesa.';
    byId('client-error').hidden = true;
    byId('pedir-conta').disabled = !sessionId || !navigator.onLine;
    if (!sessionId) {
      byId('lista-pedidos').innerHTML = '<p class="empty-state">Nenhuma sessão aberta nesta mesa.</p>';
      byId('resumo-conta').textContent = 'Aguardando abertura da sessão.';
      lastOrders = ''; lastBill = '';
      return;
    }
    const [orders, bill] = await Promise.all([api(`${base}pedidos/`), api(`${base}conta/`)]);
    if (attempt && orders.some(p => p.chave_envio === attempt.chave_envio)) {
      attempt = null; saveAttempt(); cart = []; saveCart(); renderCart();
      byId('revisao-dialog').close(); feedback('Pedido recebido pela cozinha.');
    }
    const signature = JSON.stringify(orders);
    if (signature !== lastOrders) {
      lastOrders = signature;
      byId('lista-pedidos').innerHTML = orders.length ? orders.map(p => `<article class="surface order-card"><div class="order-header"><strong>Pedido #${p.id}</strong><span class="status-label ${p.status.toLowerCase()}">${statusNames[p.status]}</span></div>${itemList(p)}<div class="order-bottom"><span class="small muted">${new Date(p.created_at).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit',timeZone:'America/Sao_Paulo'})}</span><strong>${money(p.valor_total)}</strong></div><div class="status-track" aria-label="Etapa: ${statusNames[p.status]}">${['RECEBIDO','EM_PREPARACAO','PRONTO','A_CAMINHO','ENTREGUE'].map((s,i) => `<span class="${i <= ['RECEBIDO','EM_PREPARACAO','PRONTO','A_CAMINHO','ENTREGUE'].indexOf(p.status) ? 'done' : ''}" title="${statusNames[s]}"></span>`).join('')}</div></article>`).join('') : '<p class="empty-state">Seus pedidos aparecerão aqui assim que você enviar o primeiro.</p>';
    }
    if (JSON.stringify(bill) !== lastBill) {
      lastBill = JSON.stringify(bill);
      byId('resumo-conta').innerHTML = bill.pedidos.map(p => `<div class="bill-row"><span>Pedido #${p.id} · ${statusNames[p.status]}</span><strong>${money(p.status === 'CANCELADO' ? 0 : p.valor_total)}</strong></div>`).join('') + `<div class="cart-total"><span>Total da sessão</span><strong>${money(bill.valor_total)}</strong></div>${bill.conta_solicitada ? '<p class="success-text">O garçom já foi avisado. O pagamento será simulado no atendimento.</p>' : ''}`;
    }
    byId('pedir-conta').disabled = bill.conta_solicitada || !navigator.onLine;
    byId('pedir-conta').textContent = bill.conta_solicitada ? 'Conta solicitada ✓' : 'Pedir a conta';
    } catch (error) {
      byId('client-error-message').textContent = error.message;
      byId('client-error').hidden = false;
      throw error;
    } finally { refreshing = false; }
  }
  document.addEventListener('click', event => {
    const button = event.target.closest('button');
    if (!button) return;
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
  byId('buscar-produto').addEventListener('input', event => { search = event.target.value.trim(); renderProducts(); });
  byId('tentar-novamente').addEventListener('click', () => refresh().catch(e => feedback(e.message, true)));
  byId('produto-form').addEventListener('submit', event => {
    event.preventDefault();
    currentProduct = products.find(p => p.id === currentProduct?.id);
    if (!sessionId || !currentProduct?.disponivel || attempt) { feedback('Este item não pode ser adicionado agora.', true); return; }
    const ids = [...document.querySelectorAll('[name="adicional"]:checked')].map(n => Number(n.value));
    cart.push({produto_id: currentProduct.id, nome: currentProduct.nome, preco: currentProduct.preco, quantidade: Number(byId('produto-quantidade').value), adicionais: currentProduct.adicionais.filter(a => ids.includes(a.id)), observacao: byId('produto-observacao').value.trim()});
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
    if (!cart.length || (!cartAvailable() && !attempt)) return;
    renderReview();
  });
  byId('confirmar').addEventListener('click', async () => {
    if (sending || !cart.length) return;
    try { await refresh(); } catch (error) { feedback(error.message, true); return; }
    if (sending) return;
    if (!cart.length || (!cartAvailable() && !attempt)) return;
    if (!attempt && cartSignature() !== reviewSignature) { renderReview(); feedback('O carrinho ou os preços mudaram. Confira o novo total e confirme novamente.', true); return; }
    sending = true; byId('confirmar').disabled = true; byId('confirmar').textContent = 'Enviando…';
    try {
      if (!attempt) {
        attempt = {chave_envio:MF.uuid(), mesa_uuid:token, sessao_id:sessionId, total_esperado:total().toFixed(2), observacao:byId('observacao-pedido').value, itens:cart.map(i => ({produto_id:i.produto_id, quantidade:i.quantidade, observacao:i.observacao, adicionais_ids:i.adicionais.map(a => a.id)}))};
        saveAttempt();
      }
      await api('/api/pedidos/criar/', {method:'POST', body:JSON.stringify(attempt)});
      attempt = null; saveAttempt();
      cart = []; saveCart(); byId('observacao-pedido').value = ''; byId('revisao-dialog').close();
      feedback('Pedido enviado! A cozinha já recebeu.'); await refresh();
      byId('pedidos').scrollIntoView({behavior:'smooth'});
    } catch (error) { if (error.status && error.status < 500) { attempt = null; saveAttempt(); } feedback(`${error.message} Confira os pedidos antes de tentar novamente.`, true); await loadMenu().catch(() => {}); }
    finally { sending = false; byId('confirmar').disabled = false; byId('confirmar').textContent = 'Confirmar e enviar pedido →'; renderCart(); refresh().catch(e => feedback(e.message, true)); }
  });
  byId('pedir-conta').addEventListener('click', async () => {
    byId('pedir-conta').disabled = true;
    try { await api(`${base}solicitar-conta/`, {method:'POST'}); feedback('Conta solicitada. O garçom vem ajudar você.'); await refresh(); }
    catch (error) { feedback(error.message,true); byId('pedir-conta').disabled = false; }
  });
  window.addEventListener('offline', renderCart);
  window.addEventListener('online', () => { renderCart(); refresh().catch(e => feedback(e.message,true)); });
  new IntersectionObserver(entries => {
    cartInView = entries[0].isIntersecting;
    byId('cart-shortcut').hidden = !cart.length || cartInView;
  }).observe(byId('carrinho'));
  poll(refresh);
})();
