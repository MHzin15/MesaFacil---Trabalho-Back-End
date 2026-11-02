'use strict';
(() => {
  const {api, escape, feedback, poll, orderCard, money, statusNames} = MF;
  const byId = id => document.getElementById(id);
  const labels = {livre:'Livre', ocupada:'Ocupada', aguardando_conta:'Aguardando conta'};
  let busy = false, refreshing = false, selected = null, lastData = '';
  const billUrl = id => `/api/sessoes/${id}/conta/`;
  let reviewedBill = null, currentBill = null;
  let tablesCache = [], tableFilter = '';

  function renderTables() {
    const search = StaffUI.normalize(byId('buscar-mesa').value.trim()).replace(/^mesa\s*/, '').replace(/^0+(?=\d)/, '');
    const visible = tablesCache.filter(t => (!tableFilter || t.status === tableFilter) && String(t.numero).includes(search));
    const free = tablesCache.filter(t => t.status === 'livre').length;
    byId('mesas-summary').textContent = `${visible.length} de ${tablesCache.length} mesas · ${free} livres`;
    byId('mapa-mesas').innerHTML = visible.map(t => `<article class="surface table-card table-${t.status}"><div class="section-title"><h3>Mesa ${String(t.numero).padStart(2,'0')}</h3><span class="status-label">${labels[t.status]}</span></div><p class="table-hint">${t.sessao_ativa_id ? 'Atendimento em andamento.' : 'O primeiro pedido abre o atendimento automaticamente.'}</p><div class="table-actions">${t.comandas_abertas.map(c => `<button class="btn btn-outline-primary" data-bill="${c.id}">Comanda #${c.id}${c.conta_solicitada ? " · conta solicitada" : " · conferir"}</button>`).join("")}<a class="text-link" href="/mesa/${escape(t.token_uuid)}/" target="_blank" rel="noopener">Abrir cardápio da mesa ↗</a></div></article>`).join('') || '<div class="surface workspace-empty"><h3>Nenhuma mesa encontrada</h3><p>Tente outro número ou situação.</p><button type="button" class="btn btn-outline-primary" data-clear-tables>Limpar filtros</button></div>';
  }

  function renderDeliveries(orders) {
    for (const [status, id, countId, empty] of [
      ['PRONTO','entregas-prontos','prontos-count','Nenhum pedido pronto para retirar.'],
      ['A_CAMINHO','entregas-caminho','caminho-count','Nenhuma entrega em andamento.'],
    ]) {
      const visible = orders.filter(p => p.status === status);
      StaffUI.count(countId, visible.length);
      byId(id).innerHTML = visible.map(p => orderCard(p, `<button class="btn btn-primary w-100" data-order="${p.id}" data-status="${status === 'PRONTO' ? 'A_CAMINHO' : 'ENTREGUE'}">${status === 'PRONTO' ? 'Levar à mesa' : 'Confirmar entrega'}</button>`)).join('') || `<p class="empty-state">${empty}</p>`;
    }
  }

  function showBill(bill) {
    currentBill = bill;
    if (!reviewedBill || reviewedBill.sessao_id !== bill.sessao_id) reviewedBill = {sessao_id:bill.sessao_id, versao_conta:bill.versao_conta, total_esperado:bill.valor_total};
    const changed = reviewedBill.versao_conta !== bill.versao_conta || reviewedBill.total_esperado !== bill.valor_total;
    byId('conta-alterada').hidden = !changed;
    byId('conferir-conta').hidden = !changed;
    byId('retomar-atendimento').hidden = !bill.conta_solicitada;
    byId('retomar-atendimento').disabled = busy;

    byId('conta-titulo').textContent = `Comanda #${bill.sessao_id} · Mesa ${bill.mesa.numero}`;
    byId('conta-itens').innerHTML = bill.pedidos.map(p => `<div class="bill-row"><div><strong>Pedido #${p.id}</strong><p class="small muted mb-0">${statusNames[p.status]}${p.status === 'CANCELADO' ? ' · sem cobrança' : ''}</p>${MF.itemList(p)}</div><strong>${money(p.status === 'CANCELADO' ? 0 : p.valor_total)}</strong></div>`).join('') || '<p class="empty-state">Esta sessão ainda não tem pedidos.</p>';
    byId('conta-valor').textContent = money(bill.valor_total);
    const pending = bill.pedidos.some(p => !['ENTREGUE','CANCELADO'].includes(p.status));
    byId('conta-pendencias').hidden = !pending;
    byId('conta-pendencias').textContent = 'Há pedidos pendentes. Entregue ou cancele os pedidos antes de finalizar a conta.';
    byId('pagamento-ajuda').textContent = pending ? 'O pagamento será liberado quando não houver pedidos pendentes.' : Number(bill.valor_total) === 0 ? 'Não há valor a cobrar. Você pode encerrar a sessão sem cobrança.' : 'Confira o valor e escolha o meio informado pelo cliente.';
    byId('pagamento-form').hidden = Number(bill.valor_total) === 0;
    byId('pagar').disabled = changed || pending || busy || Number(bill.valor_total) === 0 || !navigator.onLine;
    byId('fechar-sem-cobranca').hidden = pending || Number(bill.valor_total) !== 0;
    byId('fechar-sem-cobranca').disabled = changed || busy || !navigator.onLine;
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
        tablesCache = tables;
        StaffUI.count('mesas-livres', tables.filter(t => t.status === 'livre').length);
        StaffUI.count('total-entregas', panel.pedidos_prontos.length);
        StaffUI.count('total-contas', panel.comandas_aguardando_conta.length);
        renderTables();
        renderDeliveries(panel.pedidos_prontos);
        byId('contas-pendentes').innerHTML = panel.comandas_aguardando_conta.map(t => `<article class="surface table-card table-aguardando_conta"><p class="eyebrow">CONTA SOLICITADA</p><h3>Mesa ${t.mesa_numero} · Comanda #${t.id}</h3><p class="muted small">Confira os pedidos antes de finalizar.</p><button class="btn btn-primary w-100" data-bill="${t.id}">Conferir e finalizar</button></article>`).join('') || '<div class="surface workspace-empty"><h3>Nenhuma conta solicitada</h3><p>As mesas que pedirem o fechamento aparecerão aqui automaticamente.</p></div>';
      }
      if (selected && byId('conta-dialog').open) {
        const table = tables.find(t => t.comandas_abertas.some(c => c.id === selected));
        if (table) showBill(await api(billUrl(selected)));
        else { selected = null; byId('conta-dialog').close(); feedback('Esta sessão já foi encerrada.'); }
      }
      StaffUI.synced();
    } catch (error) { StaffUI.error(error.message); throw error; }
    finally { refreshing = false; }
  }

  async function action(work, success) {
    if (busy || !navigator.onLine) return;
    busy = true;
    byId('conta-error').hidden = true;
    document.querySelectorAll('button[data-open], button[data-order], #retomar-atendimento, #pagar, #fechar-sem-cobranca, #solicitar-conta').forEach(b => b.disabled = true);
    try { await work(); feedback(success); }
    catch (error) { feedback(error.message, true); byId('conta-error').textContent = error.message; byId('conta-error').hidden = false; }
    finally {
      busy = false; lastData = '';
      document.querySelectorAll('button[data-open], button[data-order]').forEach(b => b.disabled = false);
      await refresh().catch(e => feedback(e.message, true));
    }
  }

  document.addEventListener('click', async event => {
    const filter = event.target.closest('[data-table-filter], [data-clear-tables]');
    if (filter) {
      tableFilter = filter.dataset.tableFilter || '';
      if (filter.hasAttribute('data-clear-tables')) byId('buscar-mesa').value = '';
      document.querySelectorAll('[data-table-filter]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.tableFilter === tableFilter)));
      renderTables(); return;
    }
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
  byId('buscar-mesa').addEventListener('input', renderTables);
  byId('conferir-conta').addEventListener('click', () => {
    if (!currentBill) return;
    reviewedBill = {sessao_id:currentBill.sessao_id, versao_conta:currentBill.versao_conta, total_esperado:currentBill.valor_total};
    showBill(currentBill);
  });
  byId('retomar-atendimento').addEventListener('click', () => action(() => api(`/api/sessoes/${selected}/retomar/`, {method:'POST'}), 'Atendimento retomado. Confira a conta novamente antes de cobrar.'));
  byId('solicitar-conta').addEventListener('click', () => action(() => api(`/api/sessoes/${selected}/solicitar-conta/`, {method:'POST'}), 'Conta solicitada.'));
  byId('fechar-sem-cobranca').addEventListener('click', () => action(async () => {
    await api(`/api/sessoes/${selected}/fechar/`, {method:'POST'});
    byId('conta-dialog').close(); selected = null;
  }, 'Comanda encerrada. As outras comandas da mesa continuam abertas.'));
  byId('pagamento-form').addEventListener('submit', event => {
    event.preventDefault();
    if (!reviewedBill || !currentBill || reviewedBill.versao_conta !== currentBill.versao_conta) return;
    const confirmation = {...reviewedBill, meio_pagamento:byId('meio-pagamento').value};
    action(async () => {
      await api(`/api/sessoes/${confirmation.sessao_id}/pagamento/`, {method:'POST', body:JSON.stringify(confirmation)});
      byId('conta-dialog').close(); selected = null;
    }, 'Pagamento simulado confirmado. Esta comanda foi encerrada.');
  });
  window.addEventListener('online', () => refresh().catch(e => feedback(e.message, true)));
  poll(refresh);
})();
