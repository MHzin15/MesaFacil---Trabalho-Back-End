/* Navegação do cliente: executar na fixture isolada após check_desktop. */
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('fs');
const assert = require('assert/strict');
const fixture = JSON.parse(fs.readFileSync('.tmp/browser-fixture.json', 'utf8'));
const base = process.env.MESAFACIL_URL || 'http://127.0.0.1:8765';

async function screen(page, view) {
  await page.locator(`.client-nav [data-client-link="${view}"]`).click();
  await page.waitForFunction(v => document.body.dataset.clientView === v, view);
  assert.equal(await page.locator('[data-client-screen]:visible').count(), 1);
  assert.equal(await page.locator('.client-nav [aria-current="page"]').getAttribute('data-client-link'), view);
  assert(await page.locator(`#${view}`).isVisible());
  assert(await page.evaluate(() => scrollY < 2), 'A nova tela deve abrir no topo');
}

(async () => {
  const browser = await chromium.launch({channel:'chrome',headless:true});
  try {
    const context = await browser.newContext({viewport:{width:1440,height:900}, serviceWorkers:'block', reducedMotion:'reduce'});
    const guest = await context.newPage();
    const waiter = await (await browser.newContext()).newPage();
    const errors=[];
    for (const page of [guest,waiter]) { page.setDefaultTimeout(15000); page.on('pageerror', e => errors.push(e.message)); }
    await waiter.goto(base + '/entrar/');
    await waiter.locator('#id_username').fill('browser_garcom');
    await waiter.locator('#id_password').fill(fixture.password);
    await waiter.getByRole('button', {name:'Acessar meu painel'}).click();
    await waiter.waitForURL('**/garcom/');
    const open = waiter.locator(`[data-open="${fixture.table_id}"]`);
    await waiter.locator('#mapa-mesas .table-card').first().waitFor();
    if (await open.count()) await open.click();
    const url = `${base}/mesa/${fixture.table_uuid}/`;
    await guest.goto(url);
    await guest.locator('#session-label').getByText('Sessão aberta', {exact:true}).waitFor();
    assert.equal(await guest.locator('[data-client-screen]:visible').count(),1);
    assert.equal(await guest.locator('#pedidos').isVisible(),false);
    assert.equal(await guest.locator('#conta').isVisible(),false);
    assert.equal(await guest.locator('#carrinho').isVisible(),false);
    await guest.locator('#buscar-produto').fill('hamburguer');
    await guest.locator(`[data-product="${fixture.product_id}"]`).click();
    await guest.locator('#produto-quantidade').fill('2');
    await guest.getByLabel('Bacon', {exact:false}).check();
    await guest.getByLabel('Queijo Cheddar', {exact:false}).check();
    await guest.locator('#adicionar-item').click();
    assert.equal(await guest.locator('#cart-shortcut').isVisible(),true);
    assert.match(await guest.locator('#cart-shortcut-total').innerText(),/83,80/);
    fs.mkdirSync('.tmp/screens',{recursive:true});
    await guest.locator('#feedback').waitFor({state:'hidden'});
    await guest.screenshot({path:'.tmp/screens/navigation-menu-desktop.png'});
    await screen(guest,'carrinho');
    await guest.waitForURL('**/carrinho/');
    assert.match(await guest.locator('#cart-total').innerText(),/83,80/);
    await guest.locator('#observacao-pedido').fill('Servir os pratos juntos');
    await guest.screenshot({path:'.tmp/screens/navigation-cart-desktop.png'});
    await screen(guest,'pedidos');
    await guest.waitForURL('**/pedidos/');
    assert(await guest.getByText('Nenhum pedido enviado ainda').isVisible());
    await guest.screenshot({path:'.tmp/screens/navigation-orders-desktop.png'});
    await screen(guest,'conta');
    await guest.waitForURL('**/conta/');
    assert.equal(await guest.locator('#produtos').isVisible(),false);
    await guest.screenshot({path:'.tmp/screens/navigation-bill-desktop.png'});
    await guest.goBack();
    await guest.waitForFunction(() => document.body.dataset.clientView === 'pedidos');
    await guest.goForward();
    await guest.waitForFunction(() => document.body.dataset.clientView === 'conta');
    await screen(guest,'cardapio');
    assert.equal(await guest.locator('#buscar-produto').inputValue(),'hamburguer');
    await screen(guest,'carrinho');
    assert.equal(await guest.locator('#observacao-pedido').inputValue(),'Servir os pratos juntos');
    await guest.reload();
    await guest.waitForFunction(() => document.getElementById('cart-count').textContent === '2');
    assert.equal(await guest.locator('#observacao-pedido').inputValue(),'Servir os pratos juntos');
    assert.match(await guest.locator('#cart-total').innerText(),/83,80/);

    // Endereços diretos precisam funcionar antes e depois de atualizar a página.
    const layouts=[];
    for (const [width,height] of [[1920,1080],[1366,768],[390,844]]) {
      await guest.setViewportSize({width,height});
      for (const view of ['cardapio','carrinho','pedidos','conta']) {
        const target = url + (view === 'cardapio' ? '' : view + '/');
        await guest.goto(target);
        await guest.locator('#session-label').getByText('Sessão aberta', {exact:true}).waitFor();
        await guest.waitForFunction(() => document.getElementById('conta-quantidade').textContent !== 'Consultando a conta…');
        assert.equal(await guest.locator('[data-client-screen]:visible').count(),1);
        assert(await guest.locator(`#${view}`).isVisible());
        const layout=await guest.evaluate(() => ({viewport:innerWidth, content:document.documentElement.scrollWidth}));
        assert(layout.content <= width+1, `Overflow em ${view}/${width}`);
        layouts.push({view, ...layout});
        if(width===390) {
          const nav=await guest.locator('.client-nav').boundingBox();
          assert(nav.y + nav.height <= height+1, 'Navegação móvel deve ficar acessível');
          if (view === 'carrinho' || view === 'conta') {
            const action=await guest.locator(view === 'carrinho' ? '#revisar' : '#pedir-conta').boundingBox();
            assert(action && action.y > 0 && action.y + action.height < nav.y, 'A ação principal deve ficar visível acima da navegação');
            if (view === 'carrinho') {
              await guest.locator('#revisar').click();
              await guest.locator('#revisao-dialog').waitFor({state:'visible'});
              await guest.getByRole('button', {name:'Voltar ao carrinho', exact:true}).click();
            }
          }
          await guest.screenshot({path:`.tmp/screens/navigation-${view}-mobile.png`});
        }
      }
    }
    await guest.goto(url+'#pedidos');
    await guest.waitForURL('**/pedidos/');
    assert(await guest.locator('#pedidos').isVisible());
    await guest.goto(url+'#__proto__');
    await guest.locator('#session-label').getByText('Sessão aberta', {exact:true}).waitFor();
    assert(await guest.locator('#cardapio').isVisible());
    assert.equal(await guest.locator('[data-client-screen]:visible').count(),1);
    await guest.bringToFront();
    await screen(guest,'carrinho');
    assert.equal(await guest.locator('#cart-count').innerText(),'2');

    // O rascunho não foi enviado: é possível encerrar a sessão vazia pelo garçom.
    await waiter.bringToFront();
    await waiter.locator('#mapa-mesas .table-card').filter({hasText:'Mesa 01'}).locator('[data-bill]').click();
    await waiter.locator('#conta-dialog').waitFor({state:'visible'});
    assert.match(await waiter.locator('#conta-valor').innerText(),/0,00/);
    await waiter.locator('#fechar-sem-cobranca').click();
    await guest.bringToFront();
    await guest.locator('#session-label').getByText('Sessão encerrada', {exact:true}).waitFor();
    assert.equal(await guest.locator('#cart-count').innerText(),'0');
    assert.equal(await guest.locator('#observacao-pedido').inputValue(),'');
    assert.deepEqual(errors,[]);
    const result={onlyOneScreenVisible:true, separateUrls:true, backAndForward:true, startsAtTop:true,
      cartAndNotesPreserved:true, reloadAndDeepLinks:true, searchPreserved:true, legacyLinks:true,
      closedSessionClearsDraft:true, layouts, javascriptErrors:errors};
    fs.writeFileSync('.tmp/navigation-result.json', JSON.stringify(result,null,2));
    console.log(JSON.stringify(result,null,2));
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
