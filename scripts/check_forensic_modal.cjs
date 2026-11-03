// Regressão: resposta atrasada A nunca sobrescreve a seleção B do garçom.
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const assert = require('node:assert/strict');
const nodes = new Map();
const get = id => {
  if (!nodes.has(id)) nodes.set(id, {
    id, value:'', textContent:'', innerHTML:'', hidden:false, disabled:false,
    dataset:{}, open:false, handlers:{},
    addEventListener(name, fn) { this.handlers[name] = fn; },
    setAttribute() {}, showModal() { this.open = true; }, close() { this.open = false; },
  });
  return nodes.get(id);
};
const table = [{id:1,numero:1,status:'ocupada',sessao_ativa_id:1,
  token_uuid:'synthetic-table',comandas_abertas:[{id:1},{id:2}]}];
const bill = id => ({sessao_id:id,mesa:{numero:1},pedidos:[],valor_total:'0.00',
  conta_solicitada:false,versao_conta:1});
let poll, click, deferA = false, resolveA, waitingA = false;
const posts = [];
const api = async (url, options={}) => {
  if (options.method === 'POST') { posts.push(url); return {}; }
  if (url === '/api/garcom/mapa-mesas/') return table;
  if (url === '/api/garcom/') return {pedidos_prontos:[],comandas_aguardando_conta:[]};
  if (url === '/api/sessoes/1/conta/' && deferA) {
    waitingA = true;
    return new Promise(resolve => { resolveA = resolve; });
  }
  if (url === '/api/sessoes/1/conta/') return bill(1);
  if (url === '/api/sessoes/2/conta/') return bill(2);
  throw new Error('Unexpected route '+url);
};
const document = {
  getElementById:get,
  querySelectorAll:() => [],
  addEventListener(name, handler) { if (name === 'click') click = handler; },
};
const ctx = {document, navigator:{onLine:true}, window:{addEventListener(){}},
  MF:{api,escape:String,feedback(){},poll:fn=>{poll=fn;},orderCard(){},money:String,statusNames:{},itemList(){}},
  StaffUI:{normalize:String,count(){},synced(){},error(){}},console};
vm.runInNewContext(fs.readFileSync(path.resolve('static/js/garcom.js'),'utf8'),ctx,{filename:'garcom.js'});
const openBill = id => click({target:{closest(selector){return selector.includes('data-bill') ? {dataset:{bill:String(id)}} : null;}}});
(async () => {
  await openBill(1);
  assert.equal(get('conta-titulo').textContent,'Comanda #1 · Mesa 1');
  deferA = true;
  const background = poll();
  while (!waitingA) await Promise.resolve();
  // A pessoa fecha o modal A e abre B antes de voltar a resposta do polling A.
  get('conta-dialog').close();
  await openBill(2);
  assert.equal(get('conta-titulo').textContent,'Comanda #2 · Mesa 1');
  resolveA(bill(1));
  await background;
  assert.equal(get('conta-titulo').textContent,'Comanda #2 · Mesa 1');
  await get('fechar-sem-cobranca').handlers.click();
  assert.equal(posts[0],'/api/sessoes/2/fechar/');
  console.log(JSON.stringify({resultado:'OK',modal_exibido:'Comanda #2',
    operacao_gerada:posts[0],efeito:'Título e ação permanecem na comanda B após resposta atrasada A.'}));
})().catch(error=>{console.error(error);process.exitCode=1;});
