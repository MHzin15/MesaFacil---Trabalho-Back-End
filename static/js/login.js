'use strict';
document.getElementById('mostrar-senha').addEventListener('click', event => {
  const input = document.getElementById('id_password');
  const visible = input.type === 'password';
  input.type = visible ? 'text' : 'password';
  event.currentTarget.textContent = visible ? 'Ocultar' : 'Mostrar';
  event.currentTarget.setAttribute('aria-pressed', String(visible));
});
