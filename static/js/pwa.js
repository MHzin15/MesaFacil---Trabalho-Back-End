'use strict';
(() => {
  let prompt;
  const button = document.getElementById('install-app');
  if ('serviceWorker' in navigator && window.isSecureContext) {
    navigator.serviceWorker.register('/service-worker.js', {scope:'/'}).catch(() => {
      // A aplicação online continua funcional se a instalação estiver indisponível.
    });
  }
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault(); prompt = event; if (button) button.hidden = false;
  });
  button?.addEventListener('click', async () => {
    if (!prompt) return;
    await prompt.prompt(); await prompt.userChoice;
    prompt = null; button.hidden = true;
  });
  window.addEventListener('appinstalled', () => { if (button) button.hidden = true; prompt = null; });
})();
