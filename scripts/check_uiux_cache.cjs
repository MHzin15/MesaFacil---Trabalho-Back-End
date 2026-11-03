// Regressão de atualização do PWA: CSS sem hash precisa ser revalidado;
// assets imutáveis continuam baratos e dados privados não entram no cache.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const handlers = {}, entries = new Map(), requests = [];
const response = value => ({value,ok:true,type:'basic',clone(){return response(value);}});
const origin = 'https://mesa.example';
const cache = {match:async request => entries.get(request.url || request),put:async(request,value)=>entries.set(request.url || request,value)};
let failing = false;
const context = {self:{location:{origin},addEventListener:(type,handler)=>{handlers[type]=handler;}},
  caches:{open:async()=>cache,match:async()=>undefined},URL,Response,
  fetch:async(request,options)=>{requests.push({url:request.url,options});if(failing)throw new Error('offline');return response('atual');}};
vm.runInNewContext(fs.readFileSync('templates/service-worker.js','utf8').replace(/{%.*?%}/g,''),context);
async function request(path,method='GET') {
  let result;
  handlers.fetch({request:{url:origin+path,method,mode:'cors'},respondWith:promise=>{result=promise;}});
  return result === undefined ? undefined : await result;
}
(async()=>{
  const plain = '/static/css/gestao.css', hashed = '/static/css/gestao.abcdef123456.css';
  entries.set(origin+plain,response('antigo'));
  assert.equal((await request(plain)).value,'atual');
  assert.equal(requests[0].options.cache,'no-cache');
  entries.set(origin+hashed,response('imutavel'));
  const count=requests.length;
  assert.equal((await request(hashed)).value,'imutavel');
  assert.equal(requests.length,count);
  failing=true;
  assert.equal((await request(plain)).value,'atual');
  assert.equal(await request('/api/sessoes/1/conta/'),undefined);
  assert.equal(await request('/api/pedidos/criar/','POST'),undefined);
  console.log(JSON.stringify({resultado:'OK',css:'revalida versão sem hash',imutaveis:'reutiliza cache',offline:'fallback público',privacidade:'não intercepta conta nem escrita'}));
})().catch(error=>{console.error(error);process.exitCode=1;});
