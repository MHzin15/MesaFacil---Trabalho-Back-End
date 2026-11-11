const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const fs = require('fs');
const assert = require('assert/strict');
const fixture = JSON.parse(fs.readFileSync('.tmp/browser-fixture.json','utf8'));
const base = process.env.MESAFACIL_URL || 'http://127.0.0.1:8765';
async function ready(page) {
  await page.bringToFront();
  await page.waitForFunction(() => document.getElementById('last-sync')?.textContent.startsWith('Atualizado às'));
}
async function screen(page, name) {
  await page.locator(`.staff-nav [data-staff-link="${name}"]`).click();
  assert.equal(await page.locator('[data-staff-screen]:visible').count(),1);
  assert.equal(await page.locator('.staff-nav [aria-current="page"]').getAttribute('data-staff-link'),name);
  assert(await page.evaluate(() => scrollY < 2));
}
(async()=>{
  const browser = await chromium.launch({channel:'chrome',headless:true});
  try {
    const pages={}, errors=[], layouts=[];
    fs.mkdirSync('.tmp/screens',{recursive:true});
    for (const role of ['garcom','cozinha','admin']) {
      const page=await (await browser.newContext({viewport:{width:1440,height:900},serviceWorkers:'block',reducedMotion:'reduce'})).newPage();
      pages[role]=page; page.setDefaultTimeout(15000); page.on('pageerror', e=>errors.push(e.message));
      await page.goto(base+'/entrar/');
      await page.locator('#mostrar-senha').click();
      assert.equal(await page.locator('#id_password').getAttribute('type'),'text');
      await page.locator('#mostrar-senha').click();
      await page.locator('#id_username').fill('browser_'+role);
      await page.locator('#id_password').fill(fixture.password);
      await page.getByRole('button',{name:'Acessar meu painel'}).click();
      await page.waitForURL('**/'+(role==='admin'?'admin':role)+'/');
    }
    const {garcom:waiter,cozinha:kitchen,admin}=pages;
    for(const [page,role] of [[waiter,'Garçom'],[kitchen,'Cozinha']]) {
      await ready(page);
      assert.match(await page.locator('.staff-profile').innerText(),new RegExp(role));
      assert.equal(await page.locator('.workspace-switch').count(),0);
    }
    assert.equal((await waiter.request.get(base+'/cozinha/')).status(),403);
    assert.equal((await kitchen.request.get(base+'/garcom/contas/')).status(),403);
    await ready(waiter);
    await waiter.locator('#buscar-mesa').fill('02');
    assert.equal(await waiter.locator('#mapa-mesas .table-card').count(),1);
    assert(await waiter.getByRole('heading',{name:'Mesa 02',exact:true}).isVisible());
    await waiter.locator('[data-table-filter="ocupada"]').click();
    assert(await waiter.getByText('Nenhuma mesa encontrada',{exact:true}).isVisible());
    await waiter.locator('[data-clear-tables]').click();
    assert.equal(await waiter.locator('#mapa-mesas .table-card').count(),10);
    await waiter.locator('#buscar-mesa').fill('02');
    await screen(waiter,'entregas'); await screen(waiter,'contas');
    await waiter.goBack(); await waiter.waitForFunction(()=>document.body.dataset.staffView==='entregas');
    await waiter.goForward(); await waiter.waitForFunction(()=>document.body.dataset.staffView==='contas');
    await screen(waiter,'mesas');
    assert.equal(await waiter.locator('#buscar-mesa').inputValue(),'02');
    await waiter.locator('#buscar-mesa').fill('');
    await ready(kitchen); await screen(kitchen,'disponibilidade');
    await kitchen.locator('#buscar-disponibilidade').fill('hamburguer');
    await kitchen.locator('#categoria-disponibilidade').selectOption({label:'Hambúrgueres'});
    assert.equal(await kitchen.locator('#disponibilidade [data-product]').count(),3);
    const product=kitchen.locator(`[data-product="${fixture.product_id}"]`);
    await product.click();
    await kitchen.waitForFunction(id=>document.querySelector(`[data-product="${id}"]`)?.getAttribute('aria-checked')==='false',fixture.product_id);
    await kitchen.locator('#filtro-disponibilidade').selectOption('false');
    assert.equal(await kitchen.locator('#disponibilidade [data-product]').count(),1);
    await product.click();
    await kitchen.getByText('Nenhum produto encontrado',{exact:true}).waitFor();
    await kitchen.locator('#filtro-disponibilidade').selectOption('');
    await kitchen.locator('#buscar-disponibilidade').fill('');
    await kitchen.locator('#categoria-disponibilidade').selectOption('');
    await kitchen.context().route('**/api/cozinha/',route=>route.abort('failed'));
    await kitchen.locator('#refresh').click();
    await kitchen.locator('#workspace-error').waitFor({state:'visible'});
    await kitchen.context().unroute('**/api/cozinha/');
    await kitchen.locator('#retry-workspace').click();
    await kitchen.locator('#workspace-error').waitFor({state:'hidden'});

    await admin.bringToFront();
    assert(await admin.getByRole('heading',{name:'Administração do restaurante',exact:true}).isVisible());
    await admin.screenshot({path:'.tmp/screens/staff-admin-desktop.png'});
    await admin.getByRole('link',{name:'Gerenciar equipe'}).click();
    assert(await admin.locator('th.column-perfil_equipe').isVisible());
    assert(await admin.getByText('Garçom',{exact:true}).count());
    await admin.screenshot({path:'.tmp/screens/staff-equipe-desktop.png'});
    await admin.goto(base+'/garcom/'); await ready(admin);
    await admin.getByRole('link',{name:'Cozinha',exact:true}).click();
    await admin.waitForURL('**/cozinha/'); await ready(admin);
    await admin.goBack(); await admin.waitForURL('**/garcom/'); await ready(admin);
    const before=await admin.locator('#last-sync').innerText();
    await admin.waitForFunction(old=>document.getElementById('last-sync').textContent!==old,before,{timeout:10000});
    assert(await admin.getByRole('link',{name:'Administração',exact:true}).isVisible());

    for(const [width,height] of [[1440,900],[1024,768],[390,844]]) {
      for(const [role,paths] of [['garcom',['/garcom/','/garcom/entregas/','/garcom/contas/']],['cozinha',['/cozinha/','/cozinha/disponibilidade/']],['admin',['/admin/']]]) {
        const page=pages[role]; await page.setViewportSize({width,height});
        for(const path of paths) {
          await page.goto(base+path);
          if(role!=='admin') {await ready(page); assert.equal(await page.locator('[data-staff-screen]:visible').count(),1);}
          const layout=await page.evaluate(()=>({viewport:innerWidth,content:document.documentElement.scrollWidth}));
          assert(layout.content<=width+1,`${role}/${path}/${width} com overflow`);
          layouts.push({role,path,...layout});
          const slug=path.replaceAll('/','-').replace(/^-|-$/g,'');
          await page.screenshot({path:`.tmp/screens/staff-${slug}-${width}.png`});
        }
      }
    }
    assert.deepEqual(errors,[]);
    const result={roleLoginPreserved:true,roleBoundaries:true,separateStaffScreens:true,tableSearchAndFilters:true,
      availabilityFilters:true,availabilityRestored:true,loadFailureRecovery:true,adminManagementLinks:true,
      teamRoleVisible:true,historyAndPolling:true,layouts,javascriptErrors:errors};
    fs.writeFileSync('.tmp/staff-ux-result.json',JSON.stringify(result,null,2)); console.log(JSON.stringify(result,null,2));
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
