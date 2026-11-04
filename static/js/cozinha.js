'use strict';
(() => {
  const {api, escape, feedback, poll, orderCard} = MF;
  let busy = false, refreshing = false, lastData = '', lastMenu = '';
  let queue = {}, categories = [];
  const byId = id => document.getElementById(id);
  let stage = window.matchMedia('(max-width:900px)').matches ? 'RECEBIDO' : 'TODOS';
  const preference = byId('kitchen-attention');
  try { preference.value = localStorage.getItem('mf-kitchen-attention') || '0'; } catch {}
  if (!preference.value || !preference.validity.valid) preference.value = '0';
  function attentionStatus() {
    const minutes = Number(preference.value);
    byId('kitchen-attention-status').textContent = minutes > 0 ? `Ativado · após ${minutes} min` : 'Desativado';
    MF.updateAges();
  }
  attentionStatus();
  preference.addEventListener('change', () => {
    if (!preference.reportValidity()) return;
    try { localStorage.setItem('mf-kitchen-attention', preference.value); } catch {}
    attentionStatus();
  });
  document.querySelectorAll('[data-kitchen-stage]').forEach(button => button.addEventListener('click', () => {
    stage = button.dataset.kitchenStage; renderQueue();
  }));
  function renderQueue() {
    document.querySelectorAll('[data-kitchen-stage]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.kitchenStage === stage)));
    document.querySelectorAll('.kanban-column').forEach(column => { column.hidden = stage !== 'TODOS' && !column.querySelector(`#${stage}`); });
    document.querySelector('.kanban').classList.toggle('single-stage', stage !== 'TODOS');
    const search = StaffUI.normalize(byId('buscar-pedido').value.trim()).replace(/^#\s*/, '').replace(/^mesa\s*0*(?=\d)/, 'mesa ');
    for (const [status, orders] of Object.entries(queue)) {
      const visible = orders.filter(p => StaffUI.normalize(`mesa ${p.mesa_numero} comanda ${p.sessao} ${p.id} ${p.observacao || ''} ${p.itens.map(i => `${i.produto_nome} ${i.observacao} ${(i.opcoes || []).map(o => o.opcao).join(' ')} ${i.itens_adicionais.map(a => a.nome).join(' ')}`).join(' ')}`).includes(search));
      StaffUI.count(`count-${status}`, visible.length);
      StaffUI.count(`stage-${status}`, visible.length);
      byId(status).innerHTML = visible.map(p => orderCard(p, p.proximo_status ? `<button class="btn btn-primary w-100 mt-3" data-order="${p.id}" data-status="${p.proximo_status}" ${busy ? 'disabled' : ''}>${status === 'RECEBIDO' ? 'Aceitar e iniciar preparo →' : 'Marcar como pronto ✓'}</button>${status === 'RECEBIDO' ? `<button class="btn btn-outline-danger w-100 mt-2" data-order="${p.id}" data-status="CANCELADO" ${busy ? 'disabled' : ''}>Cancelar pedido</button>` : ''}` : '<p class="success-text small mt-3 mb-0">Aguardando retirada pelo garçom</p>')).join('') || `<p class="empty-state">${search ? 'Nenhum pedido nesta busca.' : 'Nenhum pedido nesta etapa.'}</p>`;
    }
    MF.updateAges();
  }
  function renderAvailability() {
    const search = StaffUI.normalize(byId('buscar-disponibilidade').value.trim());
    const category = byId('categoria-disponibilidade').value;
    const availability = byId('filtro-disponibilidade').value;
    const products = categories.flatMap(c => c.produtos.map(p => ({...p, categoria_nome:c.nome, categoria_id:String(c.id)})));
    const visible = products.filter(p => (!category || p.categoria_id === category) && (!availability || String(p.disponivel) === availability) && StaffUI.normalize(p.nome).includes(search));
    byId('disponibilidade').innerHTML = visible.map(p => `<div class="availability-item"><div><p class="availability-category">${escape(p.categoria_nome)}</p><strong>${escape(p.nome)}</strong><p class="small muted mb-0">${p.disponivel ? 'Disponível no cardápio' : 'Indisponível para novos pedidos'}</p></div><button class="availability-toggle ${p.disponivel ? 'on' : ''}" data-product="${p.id}" data-available="${!p.disponivel}" role="switch" aria-checked="${p.disponivel}" aria-label="Disponibilidade de ${escape(p.nome)}" ${busy ? 'disabled' : ''}><span></span></button></div>`).join('') || '<div class="surface workspace-empty"><h3>Nenhum produto encontrado</h3><p>Ajuste a busca, a categoria ou a situação.</p></div>';
  }
  async function refresh() {
    if (busy || refreshing) return;
    refreshing = true;
    try {
    const [data, menu] = await Promise.all([api('/api/cozinha/'), api('/api/cardapio/')]);
    if (JSON.stringify(data) !== lastData) {
      lastData = JSON.stringify(data);
      queue = data;
      StaffUI.count('total-cozinha', Object.values(data).reduce((sum, orders) => sum + orders.length, 0));
      renderQueue();
    }
    if (JSON.stringify(menu) !== lastMenu) {
      lastMenu = JSON.stringify(menu); categories = menu;
      const selected = byId('categoria-disponibilidade').value;
      byId('categoria-disponibilidade').innerHTML = '<option value="">Todas as categorias</option>' + categories.map(c => `<option value="${c.id}">${escape(c.nome)}</option>`).join('');
      byId('categoria-disponibilidade').value = categories.some(c => String(c.id) === selected) ? selected : '';
      renderAvailability();
    }
    StaffUI.synced();
    } catch (error) { StaffUI.error(error.message); throw error; }
    finally { refreshing = false; }
  }
  document.addEventListener('click', async event => {
    const button = event.target.closest('[data-order], [data-product], #refresh');
    if (!button || busy) return;
    if (button.id === 'refresh') { refresh().catch(e => feedback(e.message,true)); return; }
    if (button.dataset.status === 'CANCELADO' && !window.confirm(`Cancelar o pedido #${button.dataset.order} antes do preparo? Ele será retirado da cobrança.`)) return;
    busy = true; button.disabled = true;
    document.querySelectorAll('[data-order], [data-product]').forEach(b => { b.disabled = true; });
    try {
      if (button.dataset.order) await api(`/api/pedidos/${button.dataset.order}/status/`, {method:'PATCH', body:JSON.stringify({status:button.dataset.status})});
      else await api(`/api/produtos/${button.dataset.product}/disponibilidade/`, {method:'PATCH', body:JSON.stringify({disponivel:button.dataset.available === 'true'})});
      feedback('Atualizado com sucesso.');
    } catch(error) { feedback(error.message,true); }
    finally { busy = false; document.querySelectorAll('[data-order], [data-product]').forEach(b => { b.disabled = false; }); await refresh().catch(e => feedback(e.message,true)); }
  });
  byId('buscar-pedido').addEventListener('input', renderQueue);
  byId('buscar-disponibilidade').addEventListener('input', renderAvailability);
  byId('categoria-disponibilidade').addEventListener('change', renderAvailability);
  byId('filtro-disponibilidade').addEventListener('change', renderAvailability);
  renderQueue();
  poll(refresh);
})();
