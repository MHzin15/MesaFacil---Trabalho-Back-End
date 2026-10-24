'use strict';
(() => {
  const {money, escape, api, feedback, poll, statusNames, itemList} = MF;
  const token = document.body.dataset.mesa;
  const base = `/api/mesa/${token}/`;
  const byId = id => document.getElementById(id);
  let products = [], cart = [], sessionId = null, currentProduct = null, sending = false, selected = null;
  let lastOrders = '', lastBill = '';
  function saveCart() {
    try { sessionStorage.setItem(`mf-cart-${token}-${sessionId}`, JSON.stringify(cart)); } catch { /* Armazenamento pode estar indisponível. */ }
  }
  const unit = item => Number(item.preco) + item.adicionais.reduce((sum, a) => sum + Number(a.preco), 0);
  const total = () => cart.reduce((sum, item) => sum + Math.round(unit(item) * 100) * item.quantidade, 0) / 100;
  function renderCart() {
    byId('cart-items').innerHTML = cart.length ? cart.map((item, i) => `<div class="cart-item"><div><strong>${escape(item.nome)}</strong><button class="remove-button" data-remove="${i}" aria-label="Remover ${escape(item.nome)}">Remover</button></div><p class="small muted">${item.adicionais.map(a => escape(a.nome)).join(', ')}${item.observacao ? ` · ${escape(item.observacao)}` : ''}</p><div class="quantity-row"><div class="quantity-control"><button data-quantity="${i}" data-delta="-1" aria-label="Diminuir quantidade de ${escape(item.nome)}">−</button><span>${item.quantidade}</span><button data-quantity="${i}" data-delta="1" aria-label="Aumentar quantidade de ${escape(item.nome)}">+</button></div><strong>${money(unit(item) * item.quantidade)}</strong></div></div>`).join('') : '<p class="empty-state">Seu carrinho está esperando<br>o primeiro favorito.</p>';
    byId('cart-count').textContent = cart.reduce((sum, item) => sum + item.quantidade, 0);
    byId('cart-total').textContent = money(total());
    byId('revisar').disabled = !cart.length || !sessionId || !navigator.onLine || sending;
  }
  function renderProducts() {
    const visible = selected === null ? products : products.filter(p => p.categoria === selected);
    byId('produtos').innerHTML = visible.map(p => `<article class="product-card ${p.disponivel ? '' : 'unavailable'}"><div class="product-image">${p.foto ? `<img src="${escape(p.foto)}" alt="${escape(p.nome)}" loading="lazy">` : `<span aria-hidden="true" class="food-placeholder">${escape(p.nome.charAt(0))}</span>`}${!p.disponivel ? '<span class="unavailable-tag">Indisponível</span>' : ''}</div><div class="product-body"><h3>${escape(p.nome)}</h3><p>${escape(p.descricao)}</p><div class="product-footer"><strong>${money(p.preco)}</strong><button class="add-button" data-product="${p.id}" ${!p.disponivel || !sessionId ? 'disabled' : ''} aria-label="Adicionar ${escape(p.nome)}">+</button></div></div></article>`).join('') || '<p class="muted">Nenhum produto nesta categoria.</p>';
  }
  async function loadMenu() {
    const categories = await api('/api/cardapio/');
    products = categories.flatMap(c => c.produtos);
    byId('categorias').innerHTML = `<button data-category="" class="${selected === null ? 'active' : ''}">Todos</button>` + categories.map(c => `<button data-category="${c.id}" class="${selected === c.id ? 'active' : ''}">${escape(c.nome)}</button>`).join('');
    renderProducts();
  }
  async function refresh() {
    const mesa = await api(base);
    if (mesa.sessao_id !== sessionId) {
      sessionId = mesa.sessao_id;
      cart = [];
      try {
        const stored = JSON.parse(sessionStorage.getItem(`mf-cart-${token}-${sessionId}`) || '[]');
        if (Array.isArray(stored)) cart = stored.filter(i => i && Number.isInteger(i.quantidade) && i.quantidade > 0 && Array.isArray(i.adicionais));
      } catch { cart = []; }
      renderCart();
      renderProducts();
    }
    byId('session-label').textContent = sessionId ? 'Sessão aberta' : 'Aguardando abertura';
    byId('session-warning').hidden = Boolean(sessionId);
    byId('session-warning').textContent = 'Esta mesa está sem sessão aberta. Peça ao garçom para abrir antes de enviar pedidos.';
    byId('pedir-conta').disabled = !sessionId || !navigator.onLine;
    if (!sessionId) {
      byId('lista-pedidos').innerHTML = '<p class="empty-state">Nenhuma sessão aberta nesta mesa.</p>';
      byId('resumo-conta').textContent = 'Aguardando abertura da sessão.';
      lastOrders = ''; lastBill = '';
      return;
    }
    const [orders, bill] = await Promise.all([api(`${base}pedidos/`), api(`${base}conta/`)]);
    const signature = JSON.stringify(orders);
    if (signature !== lastOrders) {
      lastOrders = signature;
      byId('lista-pedidos').innerHTML = orders.length ? orders.map(p => `<article class="surface order-card"><div class="order-header"><strong>Pedido #${p.id}</strong><span class="status-label ${p.status.toLowerCase()}">${statusNames[p.status]}</span></div>${itemList(p)}<div class="order-bottom"><span class="small muted">${new Date(p.created_at).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'})}</span><strong>${money(p.valor_total)}</strong></div><div class="status-track" aria-label="Etapa: ${statusNames[p.status]}">${['RECEBIDO','EM_PREPARACAO','PRONTO','A_CAMINHO','ENTREGUE'].map((s,i) => `<span class="${i <= ['RECEBIDO','EM_PREPARACAO','PRONTO','A_CAMINHO','ENTREGUE'].indexOf(p.status) ? 'done' : ''}" title="${statusNames[s]}"></span>`).join('')}</div></article>`).join('') : '<p class="empty-state">Seus pedidos aparecerão aqui assim que você enviar o primeiro.</p>';
    }
    if (JSON.stringify(bill) !== lastBill) {
      lastBill = JSON.stringify(bill);
      byId('resumo-conta').innerHTML = bill.pedidos.map(p => `<div class="bill-row"><span>Pedido #${p.id} · ${statusNames[p.status]}</span><strong>${money(p.valor_total)}</strong></div>`).join('') + `<div class="cart-total"><span>Total da sessão</span><strong>${money(bill.valor_total)}</strong></div>${bill.conta_solicitada ? '<p class="success-text">O garçom já foi avisado. O pagamento será simulado no atendimento.</p>' : ''}`;
    }
    byId('pedir-conta').disabled = bill.conta_solicitada || !navigator.onLine;
    byId('pedir-conta').textContent = bill.conta_solicitada ? 'Conta solicitada ✓' : 'Pedir a conta';
  }
  document.addEventListener('click', event => {
    const button = event.target.closest('button');
    if (!button) return;
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
      byId('produto-adicionais').innerHTML = currentProduct.adicionais.length ? '<h3 class="small-heading">Deixe do seu jeito</h3>' + currentProduct.adicionais.map(a => `<label class="extra-option"><span><input type="checkbox" name="adicional" value="${a.id}"> ${escape(a.nome)}</span><strong>+ ${money(a.preco)}</strong></label>`).join('') : '';
      byId('produto-dialog').showModal();
    }
    if (button.dataset.remove !== undefined) { cart.splice(Number(button.dataset.remove),1); saveCart(); renderCart(); }
    if (button.dataset.quantity !== undefined) {
      const item = cart[Number(button.dataset.quantity)];
      item.quantidade = Math.min(99, Math.max(1,item.quantidade + Number(button.dataset.delta)));
      saveCart(); renderCart();
    }
  });
  byId('produto-form').addEventListener('submit', event => {
    event.preventDefault();
    if (!sessionId || !currentProduct) return;
    const ids = [...document.querySelectorAll('[name="adicional"]:checked')].map(n => Number(n.value));
    cart.push({produto_id: currentProduct.id, nome: currentProduct.nome, preco: currentProduct.preco, quantidade: Number(byId('produto-quantidade').value), adicionais: currentProduct.adicionais.filter(a => ids.includes(a.id)), observacao: byId('produto-observacao').value.trim()});
    saveCart(); renderCart(); byId('produto-dialog').close(); feedback('Adicionado ao carrinho.');
  });
  byId('revisar').addEventListener('click', () => {
    byId('revisao-itens').innerHTML = cart.map(i => `<div class="bill-row"><div><strong>${i.quantidade}× ${escape(i.nome)}</strong><p class="small muted mb-0">${i.adicionais.map(a => escape(a.nome)).join(', ')} ${escape(i.observacao)}</p></div><strong>${money(unit(i)*i.quantidade)}</strong></div>`).join('') + `<p class="small muted">${escape(byId('observacao-pedido').value)}</p>`;
    byId('revisao-total').textContent = money(total());
    byId('revisao-dialog').showModal();
  });
  byId('confirmar').addEventListener('click', async () => {
    if (sending || !cart.length) return;
    sending = true; byId('confirmar').disabled = true; byId('confirmar').textContent = 'Enviando…';
    try {
      await api('/api/pedidos/criar/', {method:'POST', body:JSON.stringify({mesa_uuid:token, sessao_id:sessionId, observacao:byId('observacao-pedido').value, itens:cart.map(i => ({produto_id:i.produto_id, quantidade:i.quantidade, observacao:i.observacao, adicionais_ids:i.adicionais.map(a => a.id)}))})});
      cart = []; saveCart(); byId('observacao-pedido').value = ''; byId('revisao-dialog').close();
      feedback('Pedido enviado! A cozinha já recebeu.'); await refresh();
      byId('pedidos').scrollIntoView({behavior:'smooth'});
    } catch (error) { feedback(`${error.message} Confira os pedidos antes de tentar novamente.`, true); await loadMenu().catch(() => {}); }
    finally { sending = false; byId('confirmar').disabled = false; byId('confirmar').textContent = 'Confirmar e enviar pedido →'; renderCart(); }
  });
  byId('pedir-conta').addEventListener('click', async () => {
    byId('pedir-conta').disabled = true;
    try { await api(`${base}solicitar-conta/`, {method:'POST'}); feedback('Conta solicitada. O garçom vem ajudar você.'); await refresh(); }
    catch (error) { feedback(error.message,true); byId('pedir-conta').disabled = false; }
  });
  window.addEventListener('offline', renderCart);
  window.addEventListener('online', () => { renderCart(); refresh().catch(e => feedback(e.message,true)); });
  (async () => { try { await refresh(); await loadMenu(); poll(refresh); } catch(error) { feedback(error.message,true); } })();
})();
