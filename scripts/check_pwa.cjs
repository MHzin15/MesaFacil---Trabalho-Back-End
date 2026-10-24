const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('fs');
const assert = require('assert/strict');
const base = process.env.MESAFACIL_URL || 'http://127.0.0.1:8765';
(async () => {
  const context = await chromium.launchPersistentContext(`.tmp/chrome-pwa-${Date.now()}`, {channel:'chrome', headless:true, viewport:{width:390,height:844},isMobile:true,hasTouch:true});
  const browser = context.browser();
  try {
    const page = await context.newPage();
    const errors = []; page.on('pageerror', e => errors.push(e.message));
    await page.goto(base + '/');
    await page.waitForFunction(() => Boolean(navigator.serviceWorker.controller));
    await page.evaluate(async () => { const r = await fetch('/api/cardapio/'); if (!r.ok) throw new Error('Cardápio falhou'); await r.json(); });
    await page.waitForFunction(async () => Boolean(await caches.match('/api/cardapio/')));
    const cdp = await context.newCDPSession(page);
    const installability = await cdp.send('Page.getInstallabilityErrors');
    const manifest = await cdp.send('Page.getAppManifest');
    assert.deepEqual(manifest.errors, []);
    assert.deepEqual(installability.installabilityErrors, []);
    const cached = await page.evaluate(async () => {
      const all = []; for (const key of await caches.keys()) for (const r of await (await caches.open(key)).keys()) all.push(new URL(r.url).pathname); return all;
    });
    assert(cached.includes('/offline/'));
    assert(cached.includes('/api/cardapio/'));
    assert(!cached.some(p => /^\/(api\/mesa|api\/sessoes|api\/pedidos|api\/garcom|api\/cozinha|admin|mesa\/)/.test(p)));
    await context.setOffline(true);
    await page.goto(base + '/cozinha/');
    await page.getByRole('button', {name:'Consultar cardápio salvo'}).click();
    await page.getByText('Hambúrguer Clássico', {exact:false}).waitFor();
    assert(await page.getByText('Nenhum envio será feito automaticamente', {exact:false}).isVisible());
    const postFailed = await page.evaluate(async () => { try { await fetch('/api/pedidos/criar/', {method:'POST'}); return false; } catch { return true; } });
    assert(postFailed);
    fs.mkdirSync('.tmp/screens', {recursive:true});
    await page.screenshot({path:'.tmp/screens/offline-mobile.png',fullPage:true});
    await context.setOffline(false);
    await page.goto(base + '/');
    assert.equal(errors.length, 0, errors.join('\n'));
    const result = {manifestErrors:manifest.errors, installabilityErrors:installability.installabilityErrors,
      serviceWorkerActive:true, offlineNavigation:true, cachedMenuReadable:true, offlinePostBlocked:true,
      privateResourcesCached:false, javascriptErrors:errors, browser:await browser.version()};
    fs.writeFileSync('.tmp/pwa-result.json',JSON.stringify(result,null,2));
    console.log(JSON.stringify(result,null,2));
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode=1; });
