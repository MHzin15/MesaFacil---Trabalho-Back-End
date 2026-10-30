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
async function price(page, value) {
  const status = await page.evaluate(async ({id,value}) => {
    const response = await fetch(`/api/produtos/${id}/`, {method:'PATCH', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRFToken':(document.querySelector('meta[name="csrf-token"]')?.content || document.querySelector('[name="csrfmiddlewaretoken"]')?.value)}, body:JSON.stringify({preco:value})});
    return response.status;
  }, {id:fixture.product_id, value});
  assert.equal(status,200);
}
(async () => {
  const browser = await chromium.launch({channel:'chrome',headless:true});
  try {
    const guestContext = await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,serviceWorkers:'block'});
    const guest = await guestContext.newPage();
    const kitchen = await (await browser.newContext()).newPage();
    const waiter = await (await browser.newContext()).newPage();
    const admin = await (await browser.newContext()).newPage();
    const errors=[];
    for (const p of [guest,kitchen,waiter,admin]) { p.setDefaultTimeout(15000); p.on('pageerror', e=>errors.push(e.message)); }
    await login(waiter,'garcom'); await login(kitchen,'cozinha'); await login(admin,'admin');
    await price(admin,'32.90');
    await waiter.bringToFront(); if(await waiter.locator(`[data-open="${fixture.table_id}"]`).count()) await waiter.locator(`[data-open="${fixture.table_id}"]`).click();
    await guest.goto(`${base}/mesa/${fixture.table_uuid}/`);
    const add=guest.locator(`[data-product="${fixture.product_id}"]`);
    await guest.locator('#session-label').getByText('Sessão aberta').waitFor();
    await kitchen.bringToFront(); await kitchen.locator('.staff-nav [data-staff-link="disponibilidade"]').click(); await kitchen.locator(`[data-product="${fixture.product_id}"]`).click();
    await guest.bringToFront(); await guest.waitForFunction(id=>document.querySelector(`[data-product="${id}"]`)?.disabled,fixture.product_id);
    await kitchen.bringToFront(); await kitchen.locator(`[data-product="${fixture.product_id}"]`).click();
    await guest.bringToFront(); await guest.waitForFunction(id=>document.querySelector(`[data-product="${id}"]`)?.disabled===false,fixture.product_id);
    async function addItem() {
      await guest.locator('.client-nav [data-client-link="cardapio"]').click();
      await add.click(); await guest.getByLabel('Bacon',{exact:false}).check(); await guest.getByLabel('Queijo Cheddar',{exact:false}).check();
      await guest.getByRole('button',{name:'Adicionar ao carrinho',exact:true}).click();
    }
    await addItem();
    await guest.locator('.client-nav [data-client-link="carrinho"]').click();
    await guest.locator('[data-quantity][data-delta="1"]').click();
    assert.match(await guest.locator('#cart-total').innerText(),/83,80/);
    await guest.locator('[data-remove]').click(); assert.equal(await guest.locator('#cart-count').innerText(),'0');
    await addItem();
    await guest.locator('.client-nav [data-client-link="carrinho"]').click();
    await guest.locator('#revisar').click(); await guest.locator('#revisao-dialog').waitFor({state:'visible'});
    assert.match(await guest.locator('#revisao-total').innerText(),/41,90/);
    await price(admin,'39.90');
    let sent=0;
    guest.on('request',r=>{if(r.method()==='POST' && r.url().endsWith('/api/pedidos/criar/'))sent++;});
    await guest.locator('#confirmar').click();
    await guest.waitForFunction(()=>document.getElementById('revisao-total').textContent.includes('48,90'));
    assert.equal(sent,0,'Preço mudou sem exigir uma nova revisão');
    await guest.screenshot({path:'.tmp/screens/revisao-preco-mobile.png',fullPage:false});
    let lost=false;
    await guestContext.route('**/api/pedidos/criar/',async route=>{
      const response=await route.fetch();
      if(!lost){lost=true; assert.equal(response.status(),201); await route.abort('failed');}
      else await route.fulfill({response});
    });
    await guest.locator('#confirmar').click();
    await guest.locator('#lista-pedidos .status-label').getByText('Recebido',{exact:true}).waitFor();
    await guest.waitForFunction(()=>document.getElementById('cart-count').textContent==='0');
    assert.equal(sent,1);
    const orders=await admin.evaluate(async()=> (await fetch('/api/admin/pedidos/')).json());
    const current=orders.filter(p=>p.status==='RECEBIDO');
    assert.equal(current.length,1); assert.equal(current[0].valor_total,'48.90');
    await kitchen.bringToFront();
    await kitchen.locator('.staff-nav [data-staff-link="fila"]').click();
    const cancel=kitchen.locator(`[data-order="${current[0].id}"][data-status="CANCELADO"]`);
    await cancel.waitFor(); kitchen.once('dialog',d=>d.accept()); await cancel.click();
    await guest.bringToFront(); await guest.locator('#lista-pedidos .status-label').getByText('Cancelado',{exact:true}).waitFor();
    await waiter.bringToFront(); await waiter.locator(`#mapa-mesas [data-bill="${current[0].sessao}"]`).click();
    await waiter.locator('#conta-dialog').waitFor({state:'visible'});
    assert.match(await waiter.locator('#conta-valor').innerText(),/0,00/);
    await waiter.locator('#fechar-sem-cobranca').click();
    await waiter.locator(`[data-open="${fixture.table_id}"]`).waitFor();
    await price(admin,'32.90');
    assert.deepEqual(errors,[]);
    const result={disponibilidadeSincronizada:true,carrinhoEditavel:true,novaRevisaoAposReajuste:true,
      respostaPerdidaRecuperadaSemDuplicar:true,cancelamentoAntesDoPreparo:true,encerramentoSemCobranca:true,javascriptErrors:errors};
    fs.writeFileSync('.tmp/browser-regressions.json',JSON.stringify(result,null,2)); console.log(JSON.stringify(result,null,2));
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
