/* Regressões de interação: execute após check_flow e check_regressions, na fixture isolada. */
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('fs');
const assert = require('assert/strict');
const fixture = JSON.parse(fs.readFileSync('.tmp/browser-fixture.json', 'utf8'));
const base = process.env.MESAFACIL_URL || 'http://127.0.0.1:8765';

async function login(page, role) {
  await page.goto(base + '/entrar/');
  await page.locator('#id_username').fill('browser_' + role);
  await page.locator('#id_password').fill(fixture.password);
  await page.getByRole('button', {name:'Acessar meu painel'}).click();
  await page.waitForURL('**/' + (role === 'admin' ? 'admin' : role) + '/');
}

(async () => {
  const browser = await chromium.launch({channel:'chrome', headless:true});
  try {
    const guestContext = await browser.newContext({viewport:{width:1920,height:1080}, serviceWorkers:'block', reducedMotion:'reduce'});
    const guest = await guestContext.newPage();
    const kitchen = await (await browser.newContext({viewport:{width:1440,height:900}})).newPage();
    const waiter = await (await browser.newContext({viewport:{width:1440,height:900}})).newPage();
    const admin = await (await browser.newContext({viewport:{width:1366,height:768}})).newPage();
    const errors = [];
    for (const p of [guest, kitchen, waiter, admin]) {
      p.setDefaultTimeout(15000);
      p.on('pageerror', e => errors.push(e.message));
    }
    fs.mkdirSync('.tmp/screens', {recursive:true});
    const url = `${base}/mesa/${fixture.table_uuid}/`;
    await login(waiter, 'garcom'); await login(kitchen, 'cozinha'); await login(admin, 'admin');
    await guest.goto(url);
    await guest.locator('#session-label').getByText('Aguardando abertura').waitFor();
    assert(await guest.locator('#session-warning').isVisible());
    assert(await guest.locator('[data-product]').first().isDisabled());
    assert.match(await guest.locator('#revisar-help').innerText(), /aberta pelo garçom/);
    await guest.screenshot({path:'.tmp/screens/desktop-mesa-fechada.png'});
    await waiter.bringToFront();
    await waiter.locator(`[data-open="${fixture.table_id}"]`).click();
    await guest.bringToFront();
    await guest.locator('#session-label').getByText('Sessão aberta').waitFor();

    // Buscar sem acentos, combinar categoria e limpar um resultado vazio.
    await guest.locator('#buscar-produto').fill('hamburguer');
    assert.equal(await guest.locator('.product-card').count(), 3);
    await guest.getByRole('button', {name:'Bebidas', exact:true}).click();
    await guest.getByText('Nenhum produto encontrado', {exact:true}).waitFor();
    await guest.getByRole('button', {name:'Limpar busca e filtros'}).click();
    assert.equal(await guest.locator('.product-card').count(), 15);

    // As fotos não podem invadir o texto ou interceptar o botão (defeito original).
    const add = guest.locator(`[data-product="${fixture.product_id}"]`);
    for (const button of await guest.locator('[data-product]').all()) {
      await button.click();
      await guest.locator('#produto-dialog').waitFor({state:'visible'});
      await guest.keyboard.press('Escape');
    }
    const layouts = [];
    for (const [width,height] of [[1920,1080], [1440,900], [1366,768], [1024,768], [390,844]]) {
      await guest.setViewportSize({width,height});
      await guest.locator('.client-nav [data-client-link="cardapio"]').click();
      await guest.locator('#cardapio').scrollIntoViewIfNeeded();
      const layout = await guest.evaluate(() => ({viewport:innerWidth, content:document.documentElement.scrollWidth,
        imagesContained:[...document.querySelectorAll('.product-image img')].every(img => {
          const a = img.getBoundingClientRect(), b = img.parentElement.getBoundingClientRect();
          return a.top >= b.top - 1 && a.bottom <= b.bottom + 1;
        })}));
      assert(layout.content <= width + 1, `Overflow em ${width}px`);
      assert(layout.imagesContained, `Imagem fora do contêiner em ${width}px`);
      await add.click();
      await guest.getByLabel('Bacon', {exact:false}).check();
      await guest.getByLabel('Queijo Cheddar', {exact:false}).check();
      await guest.locator('#produto-quantidade').fill('2');
      assert.match(await guest.locator('#produto-total').innerText(), /83,80/);
      const action = await guest.locator('#adicionar-item').boundingBox();
      assert(action.y >= 0 && action.y + action.height <= height, `Ação do diálogo fora da tela em ${width}px`);
      if (width === 1366) await guest.screenshot({path:'.tmp/screens/desktop-personalizacao-1366.png'});
      await guest.locator('#adicionar-item').click();
      await guest.locator('.client-nav [data-client-link="carrinho"]').click();
      assert.equal(await guest.locator('#cart-count').innerText(), '2');
      await guest.locator('[data-remove]').click();
      layouts.push({...layout, height, addAndRemove:true, dialogActionVisible:true});
    }

    await guest.setViewportSize({width:1920,height:1080});
    await guest.locator('.client-nav [data-client-link="cardapio"]').click();
    await add.focus(); await guest.keyboard.press('Enter');
    await guest.locator('#produto-dialog').waitFor({state:'visible'});
    await guest.keyboard.press('Escape');
    assert.equal(await guest.locator('#produto-dialog').evaluate(n => n.open), false);

    // Produto que fica indisponível com a personalização aberta deve explicar o bloqueio.
    await add.click();
    await kitchen.bringToFront(); await kitchen.locator('.staff-nav [data-staff-link="disponibilidade"]').click(); await kitchen.locator(`[data-product="${fixture.product_id}"]`).click();
    await guest.bringToFront();
    await guest.waitForFunction(() => document.getElementById('adicionar-item').disabled);
    assert(await guest.locator('#produto-dialog [data-dialog-feedback]').isVisible());
    assert.match(await guest.locator('#produto-dialog [data-dialog-feedback]').innerText(), /indisponível/);
    await guest.keyboard.press('Escape');
    await kitchen.bringToFront(); await kitchen.locator(`[data-product="${fixture.product_id}"]`).click();
    await guest.bringToFront();
    await guest.waitForFunction(id => document.querySelector(`[data-product="${id}"]`)?.disabled === false, fixture.product_id);

    // Vários itens: a revisão continua alcançável no carrinho em tela baixa.
    await guest.setViewportSize({width:1366,height:768});
    for (let i=0; i<6; i++) { await add.click(); await guest.locator('#adicionar-item').click(); }
    await guest.locator('.client-nav [data-client-link="carrinho"]').click();
    await guest.locator('#revisar').click();
    await guest.locator('#revisao-dialog').waitFor({state:'visible'});
    assert.equal(await guest.locator('#revisao-itens .bill-row').count(), 6);
    await guest.getByRole('button', {name:'Continuar escolhendo'}).click();
    await guest.locator('.client-nav [data-client-link="carrinho"]').click();
    while (await guest.locator('[data-remove]').count()) await guest.locator('[data-remove]').first().click();

    // Falha inicial tem mensagem persistente e recuperação pela ação Tentar novamente.
    await guestContext.route('**/api/cardapio/', route => route.abort('failed'));
    await guest.reload();
    await guest.locator('#client-error').waitFor({state:'visible'});
    await guestContext.unroute('**/api/cardapio/');
    await guest.locator('#tentar-novamente').click();
    await guest.locator('#session-label').getByText('Sessão aberta').waitFor();

    // Carrinho restaurado precisa usar os preços atuais, mesmo sem mudar o menu no polling.
    await guest.locator('.client-nav [data-client-link="cardapio"]').click();
    await add.click();
    await guest.getByLabel('Bacon', {exact:false}).check();
    await guest.getByLabel('Queijo Cheddar', {exact:false}).check();
    await guest.locator('#adicionar-item').click();
    await guest.locator('.client-nav [data-client-link="carrinho"]').click();
    await guest.evaluate(() => {
      for (const key of Object.keys(sessionStorage).filter(k => k.startsWith('mf-cart-'))) {
        const cart = JSON.parse(sessionStorage.getItem(key));
        cart.forEach(i => { i.preco='1.00'; i.adicionais.forEach(a => a.preco='1.00'); });
        sessionStorage.setItem(key, JSON.stringify(cart));
      }
    });
    await guest.reload();
    await guest.waitForFunction(() => document.getElementById('cart-total').textContent.includes('41,90'));
    await guest.setViewportSize({width:1920,height:1080});
    await guest.locator('.client-nav [data-client-link="cardapio"]').click();
    await guest.evaluate(() => scrollTo(0,0));
    await guest.screenshot({path:'.tmp/screens/desktop-cardapio-1920.png'});
    await guest.locator('.client-nav [data-client-link="carrinho"]').click();
    await guest.locator('#revisar').click();
    await guest.locator('#revisao-dialog').waitFor({state:'visible'});

    // Erro no envio precisa aparecer dentro do diálogo, acima da camada de fundo.
    await guestContext.route('**/api/pedidos/criar/', route => route.fulfill({status:400, contentType:'application/json', body:JSON.stringify({erro:'Confira os itens antes de enviar.'})}));
    await guest.locator('#confirmar').click();
    await guest.locator('#revisao-dialog [data-dialog-feedback]').waitFor({state:'visible'});
    assert.match(await guest.locator('#revisao-dialog [data-dialog-feedback]').innerText(), /Confira os itens/);
    await guest.screenshot({path:'.tmp/screens/desktop-erro-envio.png'});
    await guestContext.unroute('**/api/pedidos/criar/');
    const response = guest.waitForResponse(r => r.url().endsWith('/api/pedidos/criar/') && r.request().method()==='POST');
    await guest.locator('#confirmar').click();
    const created = await response;
    assert.equal(created.status(), 201, await created.text());
    const order = await created.json();
    assert.equal(order.valor_total, '41.90');
    await kitchen.bringToFront();
    await kitchen.locator('.staff-nav [data-staff-link="fila"]').click();
    await kitchen.locator(`[data-order="${order.id}"][data-status="EM_PREPARACAO"]`).click();
    await kitchen.screenshot({path:'.tmp/screens/desktop-cozinha.png'});
    await kitchen.locator(`[data-order="${order.id}"][data-status="PRONTO"]`).click();
    await waiter.bringToFront();
    await waiter.locator('.staff-nav [data-staff-link="entregas"]').click();
    await waiter.locator(`[data-order="${order.id}"][data-status="A_CAMINHO"]`).click();
    await waiter.locator(`[data-order="${order.id}"][data-status="ENTREGUE"]`).click();
    await guest.bringToFront();
    await guest.locator('#lista-pedidos .status-label').getByText('Entregue', {exact:true}).waitFor();
    await guest.locator('.client-nav [data-client-link="conta"]').click();
    await guest.locator('#pedir-conta').click();
    await waiter.bringToFront();
    await waiter.locator('.staff-nav [data-staff-link="contas"]').click();
    await waiter.locator('#contas-pendentes [data-bill]').click();
    await waiter.locator('#conta-dialog').waitFor({state:'visible'});
    await waiter.locator('#meio-pagamento').selectOption('PIX');
    await waiter.locator('#pagar').click();
    await waiter.locator('.staff-nav [data-staff-link="mesas"]').click();
    await waiter.locator(`[data-open="${fixture.table_id}"]`).waitFor();
    await waiter.screenshot({path:'.tmp/screens/desktop-salao.png'});

    await admin.goto(base + '/garcom/');
    await admin.getByRole('link', {name:'Salão', exact:true}).waitFor();
    assert(await admin.getByRole('link', {name:'Cozinha', exact:true}).isVisible());
    assert(await admin.getByRole('link', {name:'Administração', exact:true}).isVisible());
    await admin.locator('#mapa-mesas .table-actions a').first().waitFor();
    assert.equal(await admin.locator('#mapa-mesas .table-actions a').first().getAttribute('href'), `/mesa/${fixture.table_uuid}/`);
    const staffLayouts = {};
    for (const [name,page] of [['cozinha',kitchen], ['garcom',waiter], ['admin_salao',admin]]) {
      staffLayouts[name] = await page.evaluate(() => ({viewport:innerWidth, content:document.documentElement.scrollWidth}));
      assert(staffLayouts[name].content <= staffLayouts[name].viewport + 1, `Overflow em ${name}`);
    }
    await admin.goto(url);
    await admin.locator('#session-warning a').waitFor();
    staffLayouts.admin_cliente = await admin.evaluate(() => ({viewport:innerWidth, content:document.documentElement.scrollWidth}));
    assert(staffLayouts.admin_cliente.content <= staffLayouts.admin_cliente.viewport + 1);
    assert.deepEqual(errors, []);
    const result = {layouts, staffLayouts, allProductButtonsClicked:true, searchAndCategories:true, keyboard:true, closedSessionExplained:true,
      dialogTotal:true, unavailableProductExplained:true, longCartReview:true, initialFailureRecovery:true,
      restoredCartPrices:true, inlineSendError:true, desktopFullFlow:true, simulatedPayment:'PIX',
      staffNavigation:true, javascriptErrors:errors};
    fs.writeFileSync('.tmp/desktop-result.json', JSON.stringify(result,null,2));
    console.log(JSON.stringify(result,null,2));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode=1; });
