const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('fs');
const assert = require('assert/strict');
const fixture = JSON.parse(fs.readFileSync('.tmp/browser-fixture.json','utf8'));
const base = process.env.MESAFACIL_URL || 'http://127.0.0.1:8765';
async function login(page, role) {
  await page.goto(base + '/entrar/');
  await page.locator('#id_username').fill('browser_' + role);
  await page.locator('#id_password').fill(fixture.password);
  await page.getByRole('button', {name:'Acessar meu painel'}).click();
  await page.waitForURL('**/' + (role === 'admin' ? 'admin' : role) + '/');
}
(async () => {
  const browser = await chromium.launch({channel:'chrome',headless:true});
  try {
    const contexts = await Promise.all([
      browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true}),
      browser.newContext({viewport:{width:1280,height:800}}),
      browser.newContext({viewport:{width:1024,height:768}}),
      browser.newContext({viewport:{width:1440,height:900}})
    ]);
    const [guest, kitchen, waiter, admin] = await Promise.all(contexts.map(c => c.newPage()));
    const errors=[];
    for (const page of [guest,kitchen,waiter,admin]) {
      page.setDefaultTimeout(15000);
      page.on('pageerror', e => errors.push(e.message));
    }
    await login(waiter,'garcom');
    await login(kitchen,'cozinha');
    await guest.goto(`${base}/mesa/${fixture.table_uuid}/`);
    await waiter.bringToFront();
    if (await waiter.locator(`[data-open="${fixture.table_id}"]`).count()) await waiter.locator(`[data-open="${fixture.table_id}"]`).click();
    await guest.bringToFront();
    await guest.locator('#session-label').getByText('Sessão aberta').waitFor();
    await guest.locator(`[data-product="${fixture.product_id}"]`).click();
    await guest.locator('#produto-quantidade').fill('2');
    await guest.getByLabel('Bacon', {exact:false}).check();
    await guest.getByLabel('Queijo Cheddar', {exact:false}).check();
    await guest.locator('#produto-observacao').fill('Sem cebola');
    await guest.getByRole('button',{name:'Adicionar ao carrinho',exact:true}).click();
    await guest.locator('.client-nav [data-client-link="carrinho"]').click();
    assert.match(await guest.locator('#cart-total').innerText(),/83,80/);
    await guest.locator('#revisar').click();
    await guest.locator('#revisao-dialog').waitFor({state:'visible'});
    assert.match(await guest.locator('#revisao-total').innerText(),/83,80/);
    fs.mkdirSync('.tmp/screens',{recursive:true});
    await guest.screenshot({path:'.tmp/screens/cliente-revisao-mobile.png',fullPage:true});
    const createdPromise=guest.waitForResponse(r => r.url().endsWith('/api/pedidos/criar/') && r.request().method()==='POST');
    await guest.locator('#confirmar').click();
    const created = await createdPromise;
    assert.equal(created.status(),201,await created.text());
    const pedido = await created.json();
    assert.equal(pedido.valor_total,'83.80');
    await guest.waitForURL('**/pedidos/');
    await guest.locator('#lista-pedidos .status-label').getByText('Recebido',{exact:true}).waitFor();
    await guest.screenshot({path:'.tmp/screens/navigation-orders-mobile-live.png'});
    await guest.setViewportSize({width:1440,height:900});
    await guest.screenshot({path:'.tmp/screens/navigation-orders-desktop-live.png'});
    await guest.setViewportSize({width:390,height:844});
    await kitchen.bringToFront();
    await kitchen.locator(`[data-order="${pedido.id}"][data-status="EM_PREPARACAO"]`).click();
    await kitchen.locator(`[data-order="${pedido.id}"][data-status="PRONTO"]`).waitFor();
    assert(await kitchen.getByText('Sem cebola',{exact:true}).isVisible());
    await kitchen.screenshot({path:'.tmp/screens/cozinha-preparo.png',fullPage:true});
    await kitchen.locator(`[data-order="${pedido.id}"][data-status="PRONTO"]`).click();
    await waiter.bringToFront();
    await waiter.locator(`[data-order="${pedido.id}"][data-status="A_CAMINHO"]`).click();
    await waiter.locator(`[data-order="${pedido.id}"][data-status="ENTREGUE"]`).click();
    await guest.bringToFront();
    await guest.locator('#lista-pedidos .status-label').getByText('Entregue',{exact:true}).waitFor();
    await guest.locator('.client-nav [data-client-link="conta"]').click();
    await guest.screenshot({path:'.tmp/screens/navigation-bill-mobile-live.png'});
    await guest.locator('#pedir-conta').click();
    await waiter.bringToFront();
    await waiter.locator('#contas-pendentes [data-bill]').click();
    await waiter.locator('#conta-dialog').waitFor({state:'visible'});
    assert.match(await waiter.locator('#conta-itens').innerText(),/83,80/);
    await waiter.locator('#meio-pagamento').selectOption('CARTAO');
    await waiter.screenshot({path:'.tmp/screens/garcom-conta-tablet.png',fullPage:true});
    await waiter.locator('#pagar').click();
    await waiter.locator(`[data-open="${fixture.table_id}"]`).waitFor();
    await guest.bringToFront();
    await guest.locator('#session-label').getByText('Sessão encerrada',{exact:true}).waitFor();
    await login(admin,'admin');
    await admin.goto(`${base}/admin/restaurante/mesa/${fixture.table_id}/change/`);
    const downloadPromise=admin.waitForEvent('download');
    await admin.getByRole('link',{name:'Baixar QR Code'}).click();
    const download=await downloadPromise;
    await download.saveAs('.tmp/screens/qr-teste.png');
    const paid=await admin.evaluate(async () => (await fetch('/api/admin/contas/')).json());
    const account = paid.filter(c => c.sessao === pedido.sessao);
    assert.equal(account.length,1);
    assert.equal(account[0].valor_total,'83.80');
    assert.equal(account[0].meio_pagamento,'CARTAO');
    const cached = await waiter.evaluate(async () => {
      const all=[]; for(const k of await caches.keys()) for(const r of await(await caches.open(k)).keys()) all.push(new URL(r.url).pathname); return all;
    });
    assert(!cached.some(p => p.startsWith('/api/') && p !== '/api/cardapio/'));
    const layout={};
    for(const [name,page] of [['cliente',guest],['cozinha',kitchen],['garcom',waiter]]) {
      layout[name]=await page.evaluate(() => ({viewport:innerWidth, content:document.documentElement.scrollWidth}));
      assert(layout[name].content <= layout[name].viewport + 1, `${name} tem rolagem horizontal`);
    }
    assert.deepEqual(errors,[]);
    const result={fluxoCompleto:true,totalReferencia:'83.80',pagamento:'CARTAO',mesaLivre:true,
      qrPrivadoBaixado:true,cachePrivadoAusente:true,javascriptErrors:errors,layout,browser:await browser.version()};
    fs.writeFileSync('.tmp/browser-result.json',JSON.stringify(result,null,2));
    console.log(JSON.stringify(result,null,2));
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode=1; });
