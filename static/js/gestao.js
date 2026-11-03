'use strict';
// Uma foto removida do armazenamento não deve quebrar o cartão de gestão.
document.addEventListener('error', event => {
  const img = event.target;
  if (!(img instanceof HTMLImageElement) || !img.matches('.g-product > img')) return;
  const fallback = document.createElement('div');
  fallback.className = 'g-product-placeholder';
  fallback.setAttribute('aria-hidden', 'true');
  fallback.textContent = img.alt.charAt(0);
  img.replaceWith(fallback);
}, true);

document.querySelectorAll('.g-form').forEach(form => {
  const errors = form.querySelector('[data-form-errors]');
  errors?.focus({preventScroll:true});
  form.querySelectorAll('.g-field-error input,.g-field-error select,.g-field-error textarea').forEach(field => {
    field.setAttribute('aria-invalid','true');
    field.setAttribute('aria-describedby', `${field.getAttribute('aria-describedby') || ''} ${field.id}_errors`.trim());
  });
  form.querySelectorAll('input[type=password]').forEach(input => {
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'password-reveal';
    button.textContent = 'Mostrar senha'; button.setAttribute('aria-pressed','false');
    button.setAttribute('aria-controls', input.id);
    button.addEventListener('click', () => {
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      button.textContent = show ? 'Ocultar senha' : 'Mostrar senha';
      button.setAttribute('aria-pressed', String(show));
    });
    input.after(button);
  });
  const role = form.querySelector('[name=role]');
  if (role) {
    const summary = document.createElement('p'); summary.className = 'role-summary'; summary.id = 'role-summary';
    role.after(summary); role.setAttribute('aria-describedby', `${role.getAttribute('aria-describedby') || ''} role-summary`.trim());
    const roles = {GARCOM:'Pode consultar mesas e comandas, entregar pedidos e registrar pagamentos simulados. Não cria pedidos pelo cliente.',COZINHA:'Pode iniciar preparos, marcar pedidos prontos e pausar produtos. Não administra acessos nem registra pagamentos.',ADMIN:'Gerencia equipe, mesas, cardápio, relatórios e a operação do restaurante.'};
    const update = () => { summary.textContent = roles[role.value] || 'Escolha uma função.'; };
    role.addEventListener('change', update); update();
  }
  let dirty = false, submitting = false;
  form.addEventListener('input', () => { dirty = true; });
  form.addEventListener('change', () => { dirty = true; });
  form.addEventListener('submit', () => { submitting = true; });
  window.addEventListener('beforeunload', event => {
    if (dirty && !submitting) { event.preventDefault(); event.returnValue = ''; }
  });
});

document.querySelectorAll('[data-photo-editor]').forEach(editor => {
  const input = editor.querySelector('input[type=file]'), preview = editor.querySelector('[data-photo-preview]');
  let localUrl;
  input.addEventListener('change', () => {
    if (localUrl) URL.revokeObjectURL(localUrl);
    const file = input.files[0];
    if (!file) return;
    input.setCustomValidity(file.size > 5 * 1024 * 1024 ? 'Envie uma imagem de até 5 MB.' : '');
    if (!input.reportValidity()) return;
    localUrl = URL.createObjectURL(file); preview.src = localUrl; preview.hidden = false;
    editor.querySelector('[data-photo-empty]').hidden = true;
    const clear = editor.querySelector('input[type=checkbox]'); if (clear) clear.checked = false;
  });
  window.addEventListener('pagehide', () => { if (localUrl) URL.revokeObjectURL(localUrl); });
});
const gallery = document.getElementById('catalog-gallery');
gallery?.addEventListener('change', () => {
  document.getElementById('catalog-products').classList.toggle('gallery', gallery.checked);
});
if (/^#(?:produto|pessoa)-\d+$/.test(location.hash)) {
  const target = document.querySelector(location.hash);
  if (target) { target.setAttribute('tabindex','-1'); target.focus({preventScroll:true}); }
}
