'use strict';
// Apresentação compartilhada entre cliente e acompanhamento do garçom.
MF.renderOrders = (orders, {mesaPath = '', permitirPedido = false} = {}) => {
  const {escape, itemList, money, statusNames} = MF;
  if (!orders.length) return `<div class="surface screen-empty"><span class="empty-symbol" aria-hidden="true">✓</span><h2>Nenhum pedido enviado ainda</h2><p>${permitirPedido ? 'Depois de confirmar seu carrinho, acompanhe o preparo por aqui.' : 'Os pedidos enviados pelos clientes desta mesa aparecerão aqui.'}</p>${permitirPedido ? `<a class="btn btn-primary" href="${mesaPath}" data-client-link="cardapio">Escolher produtos</a>` : ''}</div>`;
  const steps = ['RECEBIDO', 'EM_PREPARACAO', 'PRONTO', 'A_CAMINHO', 'ENTREGUE'];
  return orders.map(p => {
    const current = steps.indexOf(p.status);
    const progress = p.status === 'CANCELADO' ? '<p class="small muted order-cancelled">Pedido cancelado antes do preparo. Não será cobrado.</p>' : `<ol class="order-progress" aria-label="Andamento do pedido">${steps.map((s, i) => `<li class="${i <= current ? 'done' : ''}" ${i === current ? 'aria-current="step"' : ''}><span aria-hidden="true">${i < current ? '✓' : i + 1}</span><small>${statusNames[s]}</small></li>`).join('')}</ol>`;
    return `<article class="surface order-card"><div class="order-header"><strong>Pedido #${p.id}</strong><span class="status-label ${p.status.toLowerCase()}">${statusNames[p.status]}</span></div><div class="order-items">${itemList(p)}${p.observacao ? `<p class="order-note">${escape(p.observacao)}</p>` : ''}</div><div class="order-bottom"><span class="small muted">${new Date(p.created_at).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit',timeZone:'America/Sao_Paulo'})}</span><strong>${money(p.valor_total)}</strong></div>${progress}</article>`;
  }).join('');
};
