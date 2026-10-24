'use strict';
(() => {
  const {api, escape, feedback, poll, orderCard} = MF;
  let busy = false, lastData = '', lastMenu = '';
  async function refresh() {
    if (busy) return;
    const [data, categories] = await Promise.all([api('/api/cozinha/'), api('/api/cardapio/')]);
    if (JSON.stringify(data) !== lastData) {
      lastData = JSON.stringify(data);
      for (const [status, orders] of Object.entries(data)) {
        document.getElementById(`count-${status}`).textContent = orders.length;
        document.getElementById(status).innerHTML = orders.map(p => orderCard(p, p.proximo_status ? `<button class="btn btn-primary w-100 mt-3" data-order="${p.id}" data-status="${p.proximo_status}">${status === 'RECEBIDO' ? 'Aceitar e iniciar preparo →' : 'Marcar como pronto ✓'}</button>${status === 'RECEBIDO' ? `<button class="btn btn-outline-danger w-100 mt-2" data-order="${p.id}" data-status="CANCELADO">Cancelar pedido</button>` : ''}` : '<p class="success-text small mt-3 mb-0">Aguardando retirada pelo garçom</p>')).join('') || '<p class="empty-state">Tudo em dia por aqui.</p>';
      }
    }
    if (JSON.stringify(categories) !== lastMenu) {
      lastMenu = JSON.stringify(categories);
      document.getElementById('disponibilidade').innerHTML = categories.flatMap(c => c.produtos).map(p => `<div class="availability-item"><div><strong>${escape(p.nome)}</strong><p class="small muted mb-0">${p.disponivel ? 'Disponível no cardápio' : 'Indisponível'}</p></div><button class="availability-toggle ${p.disponivel ? 'on' : ''}" data-product="${p.id}" data-available="${!p.disponivel}" role="switch" aria-checked="${p.disponivel}" aria-label="Disponibilidade de ${escape(p.nome)}"><span></span></button></div>`).join('');
    }
    document.getElementById('last-sync').textContent = `Atualizado às ${new Date().toLocaleTimeString('pt-BR',{timeZone:'America/Sao_Paulo'})}`;
  }
  document.addEventListener('click', async event => {
    const button = event.target.closest('[data-order], [data-product], #refresh');
    if (!button || busy) return;
    if (button.id === 'refresh') { refresh().catch(e => feedback(e.message,true)); return; }
    if (button.dataset.status === 'CANCELADO' && !window.confirm('Cancelar este pedido antes do preparo?')) return;
    busy = true; button.disabled = true;
    try {
      if (button.dataset.order) await api(`/api/pedidos/${button.dataset.order}/status/`, {method:'PATCH', body:JSON.stringify({status:button.dataset.status})});
      else await api(`/api/produtos/${button.dataset.product}/disponibilidade/`, {method:'PATCH', body:JSON.stringify({disponivel:button.dataset.available === 'true'})});
      feedback('Atualizado com sucesso.');
    } catch(error) { feedback(error.message,true); }
    finally { busy = false; button.disabled = false; await refresh().catch(e => feedback(e.message,true)); }
  });
  poll(refresh);
})();
