/* Funções compartilhadas. Dados vindos da API sempre são escapados antes do HTML. */
'use strict';
window.MF = (() => {
  const uuid = () => {
    if (crypto.randomUUID) return crypto.randomUUID();
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
    const h = [...bytes].map(n => n.toString(16).padStart(2, '0')).join('');
    return `${h.slice(0,8)}-${h.slice(8,12)}-${h.slice(12,16)}-${h.slice(16,20)}-${h.slice(20)}`;
  };
  const money = value => new Intl.NumberFormat('pt-BR', {style: 'currency', currency: 'BRL'}).format(Number(value));
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
  const statusNames = {RECEBIDO:'Recebido', EM_PREPARACAO:'Em preparação', PRONTO:'Pronto', A_CAMINHO:'A caminho', ENTREGUE:'Entregue', CANCELADO:'Cancelado'};
  let noticeTimer;
  function feedback(message, error = false) {
    const node = document.querySelector('#feedback');
    node.textContent = message;
    node.classList.toggle('error', error);
    node.hidden = false;
    clearTimeout(noticeTimer);
    noticeTimer = setTimeout(() => { node.hidden = true; }, error ? 12000 : 5000);
  }
  const message = data => {
    if (typeof data === 'string') return data;
    if (Array.isArray(data)) return data.map(message).join(' ');
    return Object.values(data || {}).map(message).join(' ');
  };
  async function api(url, options = {}) {
    const headers = {...options.headers, 'Accept': 'application/json'};
    if (options.body) headers['Content-Type'] = 'application/json';
    const method = options.method || 'GET';
    if (method !== 'GET') headers['X-CSRFToken'] = document.querySelector('meta[name="csrf-token"]').content;
    let response;
    try { response = await fetch(url, {...options, headers, credentials: 'same-origin', cache: 'no-store'}); }
    catch { throw new Error('Sem conexão com o restaurante. Confira a internet e tente novamente.'); }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 403 && document.body.dataset.page !== 'cliente') {
        throw new Error('Acesso negado ou sessão expirada. Entre novamente na área da equipe.');
      }
      const error = new Error(message(data) || 'Não foi possível concluir a ação.');
      error.status = response.status;
      throw error;
    }
    return data;
  }
  function poll(callback, interval = 4000) {
    let active = true;
    async function tick() {
      if (!active) return;
      if (!document.hidden && navigator.onLine) {
        try { await callback(); } catch (error) { feedback(error.message, true); }
      }
      if (active) setTimeout(tick, interval);
    }
    tick();
    window.addEventListener('pagehide', () => { active = false; }, {once: true});
  }
  function itemList(pedido) {
    return pedido.itens.map(item => `<div class="order-item"><strong>${item.quantidade}× ${escape(item.produto_nome)}</strong>${item.itens_adicionais.length ? `<div class="extras">+ ${item.itens_adicionais.map(a => escape(a.nome)).join(', ')}</div>` : ''}${item.observacao ? `<div class="item-note">${escape(item.observacao)}</div>` : ''}</div>`).join('');
  }
  function orderCard(pedido, action = '') {
    return `<article class="surface order-card"><div class="order-header"><strong>Mesa ${String(pedido.mesa_numero).padStart(2,'0')}</strong><span class="muted small">#${pedido.id} · ${new Date(pedido.created_at).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit',timeZone:'America/Sao_Paulo'})}</span></div>${itemList(pedido)}${pedido.observacao ? `<p class="order-note">${escape(pedido.observacao)}</p>` : ''}${action}</article>`;
  }
  document.addEventListener('click', event => {
    const button = event.target.closest('[data-close]');
    if (button) document.getElementById(button.dataset.close).close();
  });
  const connection = () => { document.querySelector('#connection').hidden = navigator.onLine; };
  window.addEventListener('online', connection);
  window.addEventListener('offline', connection);
  connection();
  return {uuid, money, escape, statusNames, api, feedback, poll, itemList, orderCard};
})();
