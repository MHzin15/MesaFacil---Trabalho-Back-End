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
