/* Verificação opcional em navegador real. Instale playwright apenas para este teste. */
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const {once}=require('node:events');
const assert=require('node:assert/strict');
const path=require('node:path');
const root=__dirname;
const python=`import tempfile, demo, server
with tempfile.TemporaryDirectory(prefix='parada-browser-') as folder:
    demo.create_demo(folder+'/demo.sqlite3')
    httpd=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
    print(httpd.server_port,flush=True)
    httpd.serve_forever()
`;
async function login(page,email){
  await page.locator('#auth-form [name=email]').fill(email);
  await page.locator('#auth-form [name=password]').fill('Parada-demo-123');
  await page.locator('#auth-submit').click();
  await page.locator('#app').waitFor({state:'visible'});
}
async function navigate(page,section){
  if(await page.locator('#menu-toggle').isVisible())await page.locator('#menu-toggle').click();
  await page.locator(`[data-page=${section}]`).click();
}
(async()=>{
  const service=spawn(process.env.PARADA_PYTHON||'python3',['-u','-c',python],{cwd:root});
  service.stderr.on('data',()=>{});
  let browser;
  try{
    const [stdout]=await once(service.stdout,'data');
    const port=Number(stdout.toString().trim());assert(port>0);
    const url=`http://127.0.0.1:${port}`;
    browser=await chromium.launch({executablePath:process.env.PARADA_BROWSER||'/opt/brave.com/brave/brave',headless:true,args:['--no-sandbox']});
    const page=await browser.newPage({viewport:{width:1440,height:1000},locale:'pt-BR'});
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    await page.goto(url);await login(page,'admin@parada.test');
    await page.locator('#dash-data .metrics').waitFor();
    assert.match(await page.locator('#dash-data').innerText(),/2h 41min/);
    await page.screenshot({path:path.join(root,'entrega','painel-desktop.png'),fullPage:true});
    await navigate(page,'people');
    const driver=page.locator('#driver-form');
    for(const [key,value] of Object.entries({name:'Motorista UI',phone:'000',document:'UI-DOC',vehicle:'Van UI',km_per_liter:'15'}))await driver.locator(`[name=${key}]`).fill(value);
    await driver.locator('[name=manager_id]').selectOption({label:'Equipe Demonstração'});
    await driver.locator('button[type=submit],button.primary').click();
    await page.locator('tr').filter({hasText:'Motorista UI'}).waitFor();
    await page.locator('tr').filter({hasText:'Motorista UI'}).getByRole('button',{name:'Editar'}).click();
    await driver.locator('[name=km_per_liter]').fill('20');
    await driver.locator('button.primary').click();
    await page.locator('tr').filter({hasText:'Motorista UI'}).filter({hasText:'20 km/l'}).waitFor();
    const user=page.locator('#user-form');
    await user.locator('[name=role]').selectOption('admin');
    assert.equal(await user.locator('[name=driver_id]').isDisabled(),true);
    assert.equal(await user.locator('[name=manager_id]').isDisabled(),true);
    await navigate(page,'settings');
    await page.locator('#settings-form [name=fuel_price]').fill('8');
    await page.locator('#settings-form button').click();
    await page.getByText('Parâmetros atualizados.',{exact:true}).waitFor();
    await navigate(page,'dashboard');
    await page.locator('#dash-data .metrics').waitFor();
    assert.match(await page.locator('#dash-data').innerText(),/50,00/);
    await navigate(page,'settings');
    await page.locator('#settings-form [name=fuel_price]').fill('6');
    await page.locator('#settings-form button').click();
    await page.getByText('Parâmetros atualizados.',{exact:true}).waitFor();
    await navigate(page,'history');
    await page.locator('#history-table tbody tr').first().waitFor();
    assert.equal(await page.locator('#history-table tbody tr').count(),9);
    const downloadPromise=page.waitForEvent('download');await page.locator('#export-history').click();
    const download=await downloadPromise;assert.equal(download.suggestedFilename(),'parada-relatorio.csv');
    await page.locator('#logout-top').click();await page.locator('#auth').waitFor({state:'visible'});
    await login(page,'gerente@parada.test');await navigate(page,'people');
    await page.locator('#driver-form').waitFor();assert.equal(await page.locator('#user-form').count(),0);
    await page.locator('#logout-top').click();await page.locator('#auth').waitFor({state:'visible'});
    await page.setViewportSize({width:390,height:844});
    await login(page,'motoristaa@parada.test');
    await page.locator('[data-route]').waitFor();assert.equal(await page.locator('[data-route]').count(),1);
    await page.locator('[data-route]').click();await page.locator('[data-stop]').first().waitFor();
    assert.equal(await page.locator('#nav [data-page=settings]').isHidden(),true);
    const stop=page.locator('[data-stop]').nth(1);
    await stop.locator('[name=departure]').fill(new Date().toLocaleDateString('sv-SE')+'T08:50:30');
    await stop.getByRole('button',{name:'Salvar horários'}).click();
    await page.getByText('Horários salvos.',{exact:true}).waitFor();
    assert.match(await page.locator('#route-detail').innerText(),/30s/);
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
    assert.equal(overflow,false,'A página não deve transbordar a largura do celular');
    await stop.locator('[name=departure]').fill(new Date().toLocaleDateString('sv-SE')+'T08:45');
    await stop.getByRole('button',{name:'Salvar horários'}).click();
    await page.getByText('Horários salvos.',{exact:true}).waitFor();
    await page.locator('#toast').evaluate(el=>el.classList.remove('show'));
    await page.screenshot({path:path.join(root,'entrega','roteiro-celular.png'),fullPage:true});
    await navigate(page,'dashboard');await page.locator('#dash-data .metrics').waitFor();
    assert.equal(await page.locator('#dash-data .metrics .metric').nth(1).locator('strong').innerText(),'1');
    await page.screenshot({path:path.join(root,'entrega','painel-celular.png'),fullPage:true});
    await page.goto(url+'/privacidade');await page.getByRole('heading',{name:'Aviso de privacidade'}).waitFor();
    assert.equal(errors.length,0,errors.join('\n'));
    console.log('PASSOU: desktop 1440px e celular 390px; cadastro/edição de motorista; perfis; parâmetros; CSV; horários com segundos; privacidade; sem erros JavaScript.');
  }finally{
    if(browser)await browser.close();
    service.kill('SIGTERM');
  }
})().catch(error=>{console.error(error);process.exitCode=1});
