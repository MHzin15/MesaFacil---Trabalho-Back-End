'use strict';
(() => {
  const {api, escape, feedback, poll, orderCard, money, statusNames} = MF;
  const byId = id => document.getElementById(id);
  const labels = {livre:'Livre', ocupada:'Ocupada', aguardando_conta:'Aguardando conta'};
  let busy = false, refreshing = false, selected = null, lastData = '';
  const billUrl = id => `/api/sessoes/${id}/conta/`;

  function showBill(bill) {
    byId('conta-titulo').textContent = `Conta · Mesa ${bill.mesa.numero}`;
    byId('conta-itens').innerHTML = bill.pedidos.map(p => `<div class="bill-row"><div><strong>Pedido #${p.id} · ${statusNames[p.status]}</strong>${MF.itemList(p)}</div><strong>${money(p.status === 'CANCELADO' ? 0 : p.valor_total)}</strong></div>`).join('') + `<div class="cart-total"><span>Total da sessão</span><strong>${money(bill.valor_total)}</strong></div>`;
    const pending = bill.pedidos.some(p => !['ENTREGUE','CANCELADO'].includes(p.status));
    byId('conta-pendencias').hidden = !pending;
    byId('pagar').disabled = pending || busy || Number(bill.valor_total) === 0 || !navigator.onLine;
    byId('fechar-sem-cobranca').hidden = pending || Number(bill.valor_total) !== 0;
    byId('fechar-sem-cobranca').disabled = busy || !navigator.onLine;
    byId('solicitar-conta').disabled = bill.conta_solicitada || busy;
    byId('solicitar-conta').textContent = bill.conta_solicitada ? 'Conta já solicitada' : 'Solicitar conta';
  }

  async function refresh() {
    if (refreshing || busy) return;
    refreshing = true;
    try {
      const [tables, panel] = await Promise.all([api('/api/garcom/mapa-mesas/'), api('/api/garcom/')]);
      const signature = JSON.stringify([tables, panel]);
      if (signature !== lastData) {
        lastData = signature;
        byId('mesas-livres').textContent = tables.filter(t => t.status === 'livre').length;
        byId('total-entregas').textContent = panel.pedidos_prontos.length;
        byId('total-contas').textContent = panel.mesas_aguardando_conta.length;
        byId('mapa-mesas').innerHTML = tables.map(t => `<article class="surface table-card table-${t.status}"><div class="section-title"><h3>Mesa ${String(t.numero).padStart(2,'0')}</h3><span class="status-label">${labels[t.status]}</span></div><p class="table-hint">${t.sessao_ativa_id ? 'Mesa aberta para receber pedidos.' : 'Abra a sessão para o cliente poder pedir.'}</p><div class="table-actions">${t.sessao_ativa_id ? `<button class="btn btn-outline-primary" data-bill="${t.sessao_ativa_id}">Ver conta e atendimento</button>` : `<button class="btn btn-primary" data-open="${t.id}">Abrir sessão</button>`}<a class="text-link" href="/mesa/${escape(t.token_uuid)}/" target="_blank" rel="noopener">Abrir cardápio da mesa ↗</a></div></article>`).join('') || '<p>Nenhuma mesa cadastrada.</p>';
        byId('entregas').innerHTML = panel.pedidos_prontos.map(p => orderCard(p, `<p class="small">${statusNames[p.status]}</p><button class="btn btn-primary w-100" data-order="${p.id}" data-status="${p.status === 'PRONTO' ? 'A_CAMINHO' : 'ENTREGUE'}">${p.status === 'PRONTO' ? 'Levar à mesa' : 'Confirmar entrega'}</button>`)).join('') || '<p class="empty-state">Nenhum pedido aguardando entrega.</p>';
        byId('contas-pendentes').innerHTML = panel.mesas_aguardando_conta.map(t => `<article class="surface table-card"><h3>Mesa ${t.numero}</h3><p>Aguardando conferência da conta.</p><button class="btn btn-outline-primary" data-bill="${t.sessao_ativa_id}">Conferir e finalizar</button></article>`).join('') || '<p class="empty-state">Nenhuma conta solicitada.</p>';
      }
      if (selected && byId('conta-dialog').open) {
        const table = tables.find(t => t.sessao_ativa_id === selected);
        if (table) showBill(await api(billUrl(selected)));
        else { selected = null; byId('conta-dialog').close(); feedback('Esta sessão já foi encerrada.'); }
      }
      byId('last-sync').textContent = `Atualizado às ${new Date().toLocaleTimeString('pt-BR',{timeZone:'America/Sao_Paulo'})}`;
    } finally { refreshing = false; }
  }

  async function action(work, success) {
    if (busy || !navigator.onLine) return;
    busy = true;
    byId('conta-error').hidden = true;
    document.querySelectorAll('button[data-open], button[data-order], #pagar, #fechar-sem-cobranca, #solicitar-conta').forEach(b => b.disabled = true);
    try { await work(); feedback(success); }
    catch (error) { feedback(error.message, true); byId('conta-error').textContent = error.message; byId('conta-error').hidden = false; }
    finally {
      busy = false; lastData = '';
      document.querySelectorAll('button[data-open], button[data-order]').forEach(b => b.disabled = false);
      await refresh().catch(e => feedback(e.message, true));
    }
  }

  document.addEventListener('click', async event => {
    const button = event.target.closest('[data-open], [data-order], [data-bill], #refresh');
    if (!button || busy) return;
    if (button.id === 'refresh') { refresh().catch(e => feedback(e.message, true)); return; }
    if (button.dataset.open) return action(() => api(`/api/mesas/${button.dataset.open}/abrir-sessao/`, {method:'POST'}), 'Sessão aberta. O cliente já pode pedir.');
    if (button.dataset.order) return action(() => api(`/api/pedidos/${button.dataset.order}/status/`, {method:'PATCH', body:JSON.stringify({status:button.dataset.status})}), 'Entrega atualizada.');
    try {
      selected = Number(button.dataset.bill);
      showBill(await api(billUrl(selected)));
      byId('conta-error').hidden = true;
      byId('conta-dialog').showModal();
    } catch (error) { feedback(error.message, true); }
  });
  byId('solicitar-conta').addEventListener('click', () => action(() => api(`/api/sessoes/${selected}/solicitar-conta/`, {method:'POST'}), 'Conta solicitada.'));
  byId('fechar-sem-cobranca').addEventListener('click', () => action(async () => {
    await api(`/api/sessoes/${selected}/fechar/`, {method:'POST'});
    byId('conta-dialog').close(); selected = null;
  }, 'Sessão encerrada. Mesa livre.'));
  byId('pagamento-form').addEventListener('submit', event => {
    event.preventDefault();
    action(async () => {
      await api(`/api/sessoes/${selected}/pagamento/`, {method:'POST', body:JSON.stringify({meio_pagamento:byId('meio-pagamento').value})});
      byId('conta-dialog').close(); selected = null;
    }, 'Pagamento aprovado! A mesa está livre.');
  });
  window.addEventListener('online', () => refresh().catch(e => feedback(e.message, true)));
  poll(refresh);
})();
