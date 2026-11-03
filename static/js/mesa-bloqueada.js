'use strict';
(() => {
  const byId = id => document.getElementById(id), token = document.body.dataset.mesa;
  const base = `/api/mesa/${token}/`, page = `/mesa/${token}/`;
  let busy = false, transferExpires = 0;
  function error(message) { byId('bloqueio-erro').textContent = message; byId('bloqueio-erro').hidden = false; }
  byId('retomar-mesa').addEventListener('click', async () => {
    if (busy) return; busy = true; byId('retomar-mesa').disabled = true;
    try { await MF.api(base + 'novo-atendimento/', {method:'POST'}); location.replace(page); }
    catch (e) { error(e.message); busy = false; byId('retomar-mesa').disabled = false; }
  });
  byId('solicitar-troca').addEventListener('click', async () => {
    if (busy) return; busy = true; byId('solicitar-troca').disabled = true;
    try {
      const request = await MF.api(base + 'transferencia/', {method:'POST'});
      transferExpires = Date.parse(request.expira_em);
      byId('troca-codigo').textContent = request.codigo; byId('troca-codigo').hidden = false;
      byId('troca-feedback').textContent = 'Mostre este código à equipe. Aguarde aqui a autorização; válido por 5 minutos.';
      byId('troca-feedback').hidden = false;
    } catch (e) { error(e.message); }
    finally { busy = false; byId('solicitar-troca').disabled = false; }
  });
  MF.poll(async () => {
    const context = await MF.api(base);
    if (context.acesso_liberado) { location.replace(page); return; }
    byId('retomar-mesa').hidden = context.mesa_em_uso;
    byId('troca-area').hidden = !context.mesa_em_uso;
    if (context.mesa_em_uso) {
      byId('bloqueio-titulo').textContent = 'Esta mesa já está em atendimento';
      byId('bloqueio-descricao').textContent = 'Uma pessoa do grupo já é responsável pelos pedidos. Peça para ela adicionar o que você deseja no celular dela.';
    } else if (context.atendimento_encerrado) {
      byId('bloqueio-titulo').textContent = 'Este acesso foi encerrado';
      byId('bloqueio-descricao').textContent = 'O atendimento foi finalizado ou o responsável foi trocado. Para uma nova visita, comece outro atendimento.';
    } else {
      byId('bloqueio-titulo').textContent = 'Esta mesa está disponível';
      byId('bloqueio-descricao').textContent = 'Toque abaixo para começar os pedidos neste aparelho.';
    }
    if (transferExpires && Date.now() >= transferExpires) {
      byId('troca-codigo').hidden = true;
      byId('troca-feedback').textContent = 'O código expirou. Solicite a troca novamente e mostre o novo código à equipe.';
      transferExpires = 0;
    }
    MF.connectionStatus('atendimento', true);
  });
})();
