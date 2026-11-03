// Usa cliente.js sem alterações em um DOM mínimo e API controlada por fase.
// Simula seleção compartilhada em cookie trocada por outra aba entre leituras.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const nodes = new Map();
const node = id => {
  if (!nodes.has(id)) nodes.set(id, {id,value:'',textContent:'',innerHTML:'',hidden:false,
    disabled:false,dataset:{},style:{},handlers:{},open:false,
    addEventListener(name,fn){this.handlers[name]=fn;},setAttribute(){},removeAttribute(){},
    querySelectorAll(){return [];},querySelector(){return node('nested');},focus(){},
    showModal(){this.open=true;},close(){this.open=false;}});
  return nodes.get(id);
};
const store = new Map();
const attempt = {atendimento_id:'draft-A',chave_envio:'original-A',mesa_uuid:'table',sessao_id:null,total_esperado:'10.00',
  observacao:'',itens:[{produto_id:1,quantidade:1,adicionais_ids:[],observacao:''}]};
store.set('mf-attempt-table-draft-A',JSON.stringify(attempt));
store.set('mf-cart-table-draft-A',JSON.stringify([{produto_id:1,nome:'Item',preco:'10.00',
  quantidade:1,adicionais:[],observacao:''}]));
const context = id => ({acesso_liberado:true,atendimento_id:`draft-${id}`,sessao_id:id==='A'?1:2,
  atendimento_encerrado:false,comandas:[]});
const bill = id => ({sessao_id:id==='A'?1:2,pedidos:[],valor_total:'0.00',conta_solicitada:false});
let phase='bootstrap', selected='A', changed=false, poll;
const sent=[];
const api = async (url,options={}) => {
  if (url==='/api/cardapio/' && phase==='menu-failure') throw new Error('Catálogo indisponível');
  if (url==='/api/cardapio/') return [{id:1,nome:'Categoria',produtos:[{id:1,nome:'Item',
    descricao:'',categoria:1,preco:'10.00',adicionais:[],disponivel:true}]}];
  if (url==='/api/mesa/table/') {
    if (phase==='race'&&!changed) {
      const read=context('A');
      // Após o servidor ler A, outra aba muda a seleção antes dos próximos GETs.
      selected='B'; changed=true;
      return read;
    }
    return context(selected);
  }
  if (url.startsWith('/api/mesa/table/pedidos/')) {
    assert.equal(new URL(url, 'http://local').searchParams.get('atendimento_id'), 'draft-A');
    if (phase==='bootstrap') throw new Error('Resposta HTTP perdida');
    if (phase==='stable') return [{id:1,sessao:1,chave_envio:'original-A'}];
    return []; // B não contém o pedido já gravado em A.
  }
  if (url.startsWith('/api/mesa/table/conta/')) {
    assert.equal(new URL(url, 'http://local').searchParams.get('atendimento_id'), 'draft-A');
    return bill('A');
  }
  if (url==='/api/pedidos/criar/') {
    sent.push({selected,payload:JSON.parse(options.body)});
    return {id:1,sessao:1};
  }
  throw new Error('Unexpected route '+url);
};
const document={body:{dataset:{mesa:'table',clientView:'carrinho'}},documentElement:{style:{}},title:'',
  getElementById:node,addEventListener(){},querySelectorAll(){return [];},
  querySelector(selector){return selector==='.table-tag strong'?{textContent:'01'}:node('selected');}};
const ctx={document,window:{addEventListener(){},scrollTo(){}},location:{pathname:'/mesa/table/carrinho/',hash:'',search:''},
  history:{pushState(){},replaceState(){}},navigator:{onLine:true},HTMLImageElement:class {},
  sessionStorage:{getItem:key=>store.get(key)||null,setItem:(key,value)=>store.set(key,value),removeItem:key=>store.delete(key)},
  URL,MF:{api,money:String,escape:String,feedback(){},poll:fn=>{poll=fn;},statusNames:{},itemList(){return '';},renderOrders(){return '';},uuid(){return 'unused';}},console};
vm.runInNewContext(fs.readFileSync('static/js/cliente.js','utf8'),ctx,{filename:'cliente.js'});
(async()=>{
  // Após a primeira gravação A, uma indisponibilidade de leitura mantém o envio pendente.
  try { await poll(); } catch {}
  phase=process.argv[2]||'race';
  await node('confirmar').handlers.click();
  if (phase==='stable') {
    assert.equal(sent.length,0);
    console.log(JSON.stringify({resultado:'CONTROLE_ESTAVEL',reenvios:0,efeito:'A chave encontrada nos pedidos A é reconhecida e o JS não reenvia.'}));
    return;
  }
  assert.equal(sent.length,1);
  assert.equal(sent[0].selected,phase==='race' ? 'B' : 'A');
  assert.equal(sent[0].payload.atendimento_id,'draft-A');
  assert.equal(node('conta-total').textContent,'0.00');
  assert.equal(sent[0].payload.chave_envio,'original-A');
  assert.equal(sent[0].payload.sessao_id,null);
  console.log(JSON.stringify({resultado:'OK',contexto_lido:'A',leituras_seguintes:'B',
    payload_reenviado:sent[0].payload.chave_envio,sessao_id:sent[0].payload.sessao_id,
    selecao_no_envio:sent[0].selected,destino_fixo:sent[0].payload.atendimento_id}));
})().catch(error=>{console.error(error);process.exitCode=1;});
