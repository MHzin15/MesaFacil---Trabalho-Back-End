'use strict';
window.StaffUI = (() => {
  const links = [...document.querySelectorAll('.staff-nav [data-staff-link]')];
  const views = new Map(links.map(link => [link.dataset.staffLink, link]));
  const title = document.getElementById('workspace-title');
  function show(view, navigate = false, focus = false) {
    const link = views.get(view);
    if (!link) return;
    const path = new URL(link.href).pathname;
    if (navigate && (location.pathname !== path || location.hash || location.search)) history.pushState(null, '', path);
    document.body.dataset.staffView = view;
    document.querySelectorAll('[data-staff-screen]').forEach(panel => { panel.hidden = panel.dataset.staffScreen !== view; });
    links.forEach(item => {
      if (item === link) item.setAttribute('aria-current', 'page');
      else item.removeAttribute('aria-current');
    });
    title.textContent = link.dataset.title;
    document.getElementById('workspace-description').textContent = link.dataset.description;
    document.title = `${link.dataset.title} · MesaFácil`;
    if (focus) {
      document.querySelectorAll('dialog[open]').forEach(dialog => dialog.close());
      window.scrollTo(0, 0);
      title.focus({preventScroll:true});
    }
  }
  document.addEventListener('click', event => {
    const link = event.target.closest('a[data-staff-link]');
    if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) return;
    event.preventDefault(); show(link.dataset.staffLink, true, true);
  });
  window.addEventListener('popstate', () => {
    const link = links.find(item => new URL(item.href).pathname === location.pathname);
    if (link) show(link.dataset.staffLink, false, true);
  });
  function error(message) {
    const node = document.getElementById('workspace-error-message');
    if (node.textContent !== message) node.textContent = message;
    document.getElementById('workspace-error').hidden = false;
  }
  function count(id, value) {
    const node = document.getElementById(id);
    if (node && node.textContent !== String(value)) node.textContent = value;
  }
  function synced() {
    document.getElementById('workspace-error').hidden = true;
    document.getElementById('last-sync').textContent = `Atualizado às ${new Date().toLocaleTimeString('pt-BR',{timeZone:'America/Sao_Paulo'})}`;
  }
  document.getElementById('retry-workspace').addEventListener('click', () => document.getElementById('refresh').click());
  document.documentElement.style.scrollBehavior = 'auto';
  const aliases = new Map([['mesas','mesas'], ['sec-entregas','entregas'], ['sec-contas','contas'], ['disponibilidade','disponibilidade']]);
  const old = aliases.get(location.hash.slice(1));
  if (views.has(old)) { history.replaceState(null, '', views.get(old).getAttribute('href')); show(old); }
  else show(document.body.dataset.staffView);
  return {show, error, synced, count, normalize:value => String(value).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase()};
})();
