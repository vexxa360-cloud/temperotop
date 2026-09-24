/**
 * Store TemperoTop — pedidos + ciclo pós-pagamento (dropshipping) + produtos.
 * -------------------------------------------------------------------------
 * Persistência em JSON (backend/data/*.json). Para volume alto, troque por um
 * banco mantendo as funções exportadas.
 *
 * TRÊS STATUS INDEPENDENTES (rastreabilidade):
 *   payment      → pendente | em_processamento | aprovado | rejeitado | cancelado | reembolsado
 *   fulfillment  → aguardando_compra | compra_realizada | aguardando_envio   (etapa do fornecedor)
 *   shippingStatus → aguardando | enviado | acompanhamento | entregue
 * A barra de progresso (10 estágios) é DERIVADA desses campos.
 *
 * Dados do fornecedor (custo, link, margem) são ADMINISTRATIVOS — nunca vão ao cliente.
 */
const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, 'data');
const ORDERS_FILE = path.join(DATA_DIR, 'orders.json');
const PRODUCTS_FILE = path.join(DATA_DIR, 'products.json');

/* ===================== rótulos ===================== */
const PAYMENT = {
  pendente: 'Pagamento pendente', em_processamento: 'Pagamento em processamento',
  aprovado: 'Pagamento aprovado', rejeitado: 'Pagamento rejeitado',
  cancelado: 'Pagamento cancelado', reembolsado: 'Pagamento reembolsado'
};
const FULFILLMENT = {
  aguardando_compra: 'Aguardando compra do fornecedor',
  compra_realizada: 'Compra realizada',
  aguardando_envio: 'Aguardando envio do fornecedor'
};
const SHIPPING = {
  aguardando: 'Aguardando processamento', enviado: 'Enviado',
  acompanhamento: 'Em acompanhamento', entregue: 'Entregue'
};
const MP_TO_PAYMENT = {
  pending: 'pendente', in_process: 'em_processamento', authorized: 'em_processamento',
  approved: 'aprovado', rejected: 'rejeitado', cancelled: 'cancelado',
  refunded: 'reembolsado', charged_back: 'reembolsado'
};

/* Fluxo mestre (10 estágios) — só para a barra de progresso */
const FLOW_STAGES = [
  'Pedido recebido', 'Pagamento pendente', 'Pagamento aprovado',
  'Aguardando compra do fornecedor', 'Compra realizada', 'Aguardando envio do fornecedor',
  'Enviado', 'Acompanhamento', 'Entregue', 'Finalizado'
];
function stageIndex(o) {
  if (o.finalizado) return 10;
  const s = o.shippingStatus, ful = o.fulfillment, p = o.payment.status;
  if (s === 'entregue') return 9;
  if (s === 'acompanhamento') return 8;
  if (s === 'enviado') return 7;
  if (ful === 'aguardando_envio') return 6;
  if (ful === 'compra_realizada') return 5;
  if (ful === 'aguardando_compra') return 4;
  if (p === 'aprovado' || p === 'em_processamento') return 3;
  if (p === 'pendente') return 2;
  return 1;
}
const paymentBlocked = o => ['rejeitado', 'cancelado', 'reembolsado'].includes(o.payment.status);

/* ===================== ações operacionais ===================== */
/* (a "compra realizada" e o "enviar com rastreio" têm formulários próprios) */
const ACTIONS = [
  { key: 'aguardar_envio', label: 'Marcar: aguardando envio do fornecedor', field: 'operacao', to: 'Aguardando envio do fornecedor',
    can: o => o.fulfillment === 'compra_realizada',
    apply: o => { o.fulfillment = 'aguardando_envio'; } },
  { key: 'acompanhar', label: 'Enviar para Acompanhamento', field: 'envio', to: 'Acompanhamento',
    can: o => o.shippingStatus === 'enviado',
    apply: o => { o.shippingStatus = 'acompanhamento'; o.tracking.ativo = true; } },
  { key: 'entregue', label: 'Marcar como Entregue', field: 'envio', to: 'Entregue',
    can: o => o.shippingStatus === 'acompanhamento',
    apply: o => { o.shippingStatus = 'entregue'; } },
  { key: 'finalizar', label: 'Finalizar Pedido', field: 'pedido', to: 'Finalizado',
    can: o => o.shippingStatus === 'entregue' && !o.finalizado,
    apply: o => { o.finalizado = true; } }
];
const getAction = key => ACTIONS.find(a => a.key === key);
/* próxima ação sugerida no painel (inclui as etapas com formulário) */
function nextStep(o) {
  if (paymentBlocked(o)) return { type: 'blocked', label: PAYMENT[o.payment.status] };
  if (o.payment.status !== 'aprovado') return { type: 'wait_payment' };
  if (o.finalizado) return { type: 'done' };
  // fase de envio (tem prioridade: já saiu da fila do fornecedor)
  if (o.shippingStatus === 'entregue') return { type: 'action', key: 'finalizar', label: 'Finalizar Pedido' };
  if (o.shippingStatus === 'acompanhamento') return { type: 'action', key: 'entregue', label: 'Marcar como Entregue' };
  if (o.shippingStatus === 'enviado') return { type: 'action', key: 'acompanhar', label: 'Enviar para Acompanhamento' };
  // fase do fornecedor
  if (o.fulfillment === 'aguardando_compra') return { type: 'form_compra', label: 'Registrar compra do fornecedor' };
  if (o.fulfillment === 'compra_realizada') return { type: 'action', key: 'aguardar_envio', label: 'Marcar: aguardando envio do fornecedor' };
  if (o.fulfillment === 'aguardando_envio') return { type: 'form_envio', label: 'Registrar rastreio e marcar como enviado' };
  return { type: 'done' };
}

/* ===================== util / persistência ===================== */
function ensure() {
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
  if (!fs.existsSync(ORDERS_FILE)) fs.writeFileSync(ORDERS_FILE, JSON.stringify({ seq: 0, orders: [] }, null, 2));
  if (!fs.existsSync(PRODUCTS_FILE)) fs.writeFileSync(PRODUCTS_FILE, JSON.stringify({ products: [defaultProduct()] }, null, 2));
}
const readJson = f => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return null; } };
const writeJson = (f, d) => { ensure(); fs.writeFileSync(f, JSON.stringify(d, null, 2)); };
const readOrders = () => { ensure(); return readJson(ORDERS_FILE) || { seq: 0, orders: [] }; };
const writeOrders = db => writeJson(ORDERS_FILE, db);
const readProducts = () => { ensure(); return readJson(PRODUCTS_FILE) || { products: [defaultProduct()] }; };
const writeProducts = db => writeJson(PRODUCTS_FILE, db);

const onlyDigits = s => String(s || '').replace(/\D/g, '');
const num = v => { const n = Number(String(v).replace(',', '.')); return isNaN(n) ? 0 : n; };
function stamp() {
  const d = new Date();
  return { iso: d.toISOString(), data: d.toLocaleDateString('pt-BR'), hora: d.toLocaleTimeString('pt-BR', { hour12: false }) };
}
function addLog(o, { field, from, to, user, origin, reason }) {
  const t = stamp();
  o.logs.unshift({ at: t.iso, data: t.data, hora: t.hora, field, from, to, user: user || 'Sistema', origin, reason: reason || '' });
}

/* ===================== PRODUTOS ===================== */
function defaultProduct() {
  return {
    sku: 'PT360-12',
    cartId: 'porta-temperos-360',
    nome: 'Porta-Temperos Giratório 360°',
    // opções de quantidade de frascos escolhidas na compra
    variants: [
      { id: '6',  frascos: 6,  precoVenda: 59.90, custoFornecedor: 0 },
      { id: '8',  frascos: 8,  precoVenda: 69.90, custoFornecedor: 0 },
      { id: '12', frascos: 12, precoVenda: 99.90, custoFornecedor: 0 }
    ],
    outrosCustos: 0,         // frete de compra, taxas, etc. (por pedido)
    fornecedor: '',
    linkFornecedor: '',      // ADMIN-ONLY — nunca vai ao cliente
    statusFornecedor: 'ativo'
  };
}
const listProducts = () => readProducts().products;
const getProduct = sku => readProducts().products.find(p => p.sku === sku) || null;
const getProductByCartId = cartId => readProducts().products.find(p => p.cartId === cartId) || readProducts().products[0] || null;
function getVariant(product, variantId) {
  const vs = product?.variants || [];
  return vs.find(v => v.id === String(variantId)) || vs[0] || { id: '6', frascos: 6, precoVenda: 0, custoFornecedor: 0 };
}
const margemVariante = (p, v) => Number((num(v.precoVenda) - num(v.custoFornecedor) - num(p.outrosCustos)).toFixed(2));
function updateProduct(sku, patch) {
  const db = readProducts();
  const p = db.products.find(x => x.sku === sku);
  if (!p) return null;
  ['nome', 'fornecedor', 'linkFornecedor', 'statusFornecedor'].forEach(k => { if (patch[k] !== undefined) p[k] = patch[k]; });
  if (patch.outrosCustos !== undefined) p.outrosCustos = num(patch.outrosCustos);
  // preços e custos por variante: campos preco_<id> e custo_<id>
  (p.variants || []).forEach(v => {
    if (patch['preco_' + v.id] !== undefined) v.precoVenda = num(patch['preco_' + v.id]);
    if (patch['custo_' + v.id] !== undefined) v.custoFornecedor = num(patch['custo_' + v.id]);
  });
  writeProducts(db);
  return p;
}

/* ===================== CEP (ViaCEP no servidor) ===================== */
async function lookupCep(cep) {
  const digits = onlyDigits(cep);
  if (digits.length !== 8) return { ok: false, reason: 'invalid' };
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 8000);
    const r = await fetch(`https://viacep.com.br/ws/${digits}/json/`, { signal: ctrl.signal });
    clearTimeout(timer);
    if (!r.ok) return { ok: false, reason: 'unavailable' };
    const d = await r.json();
    if (d.erro) return { ok: false, reason: 'not_found' };
    return { ok: true, data: {
      cep: digits.replace(/(\d{5})(\d{3})/, '$1-$2'),
      logradouro: d.logradouro || '', bairro: d.bairro || '', cidade: d.localidade || '', estado: d.uf || ''
    }};
  } catch { return { ok: false, reason: 'unavailable' }; }
}
async function buildShipping(cs = {}) {
  const r = await lookupCep(cs.cep);
  const base = r.ok ? r.data : {
    cep: onlyDigits(cs.cep).replace(/(\d{5})(\d{3})/, '$1-$2'),
    logradouro: cs.endereco || '', bairro: cs.bairro || '', cidade: cs.cidade || '', estado: cs.estado || ''
  };
  return {
    cep: base.cep, logradouro: base.logradouro || cs.endereco || '',
    numero: String(cs.numero || '').trim(), complemento: String(cs.complemento || '').trim(),
    bairro: base.bairro || cs.bairro || '', cidade: base.cidade || cs.cidade || '',
    estado: base.estado || cs.estado || '', cep_validado: r.ok, cep_status: r.ok ? 'validado' : r.reason
  };
}

/* ===================== PEDIDOS ===================== */
function createOrder({ payer, shipping, items }) {
  const db = readOrders();
  db.seq += 1;
  const number = String(db.seq).padStart(6, '0');
  const prod = getProductByCartId(items[0]?.id) || defaultProduct();
  // PREÇO definido pelo SERVIDOR a partir da variante escolhida (nunca confia no navegador)
  const variant = getVariant(prod, items[0]?.variantId);
  const qty = Number(items[0]?.quantity) || 1;
  const total = Number((num(variant.precoVenda) * qty).toFixed(2));
  const t = stamp();

  const order = {
    id: number, ref: `PEDIDO #${number}`, createdAt: t.iso,
    productSku: prod.sku, variantId: variant.id, frascos: variant.frascos,
    customer: {
      nome: payer.name || '', email: payer.email || '',
      telefone: payer.phone || '', cpf: payer.identification?.number || ''
    },
    shipping,
    items: [{ title: prod.nome, quantity: qty, unit_price: num(variant.precoVenda), variacao: `${variant.frascos} frascos de vidro` }],
    total,
    payment: { provider: 'mercadopago', preferenceId: null, status: 'pendente', confirmation: null },
    fulfillment: null,          // definido após aprovação do pagamento
    shippingStatus: 'aguardando',
    finalizado: false,
    /* dados administrativos do fornecedor (nunca vão ao cliente) */
    costs: { valorPago: total, custoFornecedor: 0, outrosCustos: 0, margemEstimada: 0, custoReal: null, margemOperacional: null, aprovadoEm: null },
    supplier: { fornecedor: '', linkProduto: '', pedidoFornecedor: '', valorPagoFornecedor: null, dataCompra: '', observacoes: '', comprovante: '' },
    tracking: { codigo: '', transportadora: '', dataPostagem: '', link: '', ativo: false },
    logs: []
  };
  addLog(order, { field: 'pedido', from: '—', to: 'Pedido recebido', origin: 'AUTOMÁTICA' });
  addLog(order, { field: 'pagamento', from: '—', to: 'Pagamento pendente', origin: 'AUTOMÁTICA' });
  db.orders.unshift(order);
  writeOrders(db);
  return order;
}
function updateOrder(id, patch) {
  const db = readOrders();
  const o = db.orders.find(x => x.id === id);
  if (!o) return null;
  Object.assign(o, patch);
  writeOrders(db);
  return o;
}
const getOrder = id => readOrders().orders.find(o => o.id === id) || null;
const listOrders = () => readOrders().orders;

/* Pagamento automático via Mercado Pago (webhook) — spec pós-pagamento */
function setPaymentFromProvider(id, mpStatus, meta = {}) {
  const db = readOrders();
  const o = db.orders.find(x => x.id === id);
  if (!o) return { error: 'Pedido não encontrado.' };
  const status = MP_TO_PAYMENT[mpStatus] || 'em_processamento';
  const from = PAYMENT[o.payment.status];
  const t = stamp();
  o.payment.status = status;
  o.payment.confirmation = {
    source: meta.source || 'Mercado Pago / Webhook', transactionId: meta.transactionId || '',
    statusReturned: mpStatus, data: t.data, hora: t.hora, at: t.iso
  };
  addLog(o, { field: 'pagamento', from, to: PAYMENT[status], user: 'Mercado Pago', origin: 'AUTOMÁTICA',
    reason: `Transação ${meta.transactionId || '—'} · status "${mpStatus}"` });

  /* Ao APROVAR: registra data/hora, calcula custo + margem e entra na fila de compra */
  if (status === 'aprovado' && !o.fulfillment) {
    const prod = getProduct(o.productSku) || defaultProduct();
    const v = getVariant(prod, o.variantId);
    o.costs.custoFornecedor = num(v.custoFornecedor);
    o.costs.outrosCustos = num(prod.outrosCustos);
    o.costs.valorPago = num(o.total);
    o.costs.margemEstimada = Number((o.costs.valorPago - o.costs.custoFornecedor - o.costs.outrosCustos).toFixed(2));
    o.costs.aprovadoEm = t.iso;
    o.supplier.fornecedor = prod.fornecedor || '';
    o.supplier.linkProduto = prod.linkFornecedor || '';
    o.fulfillment = 'aguardando_compra';
    addLog(o, { field: 'operacao', from: '—', to: 'Aguardando compra do fornecedor', user: 'Sistema', origin: 'AUTOMÁTICA',
      reason: `Custo R$ ${o.costs.custoFornecedor.toFixed(2)} · margem estimada R$ ${o.costs.margemEstimada.toFixed(2)}` });
  }
  writeOrders(db);
  return { order: o };
}

/* Alteração manual excepcional de pagamento (exige motivo + responsável) */
function overridePayment(id, status, { motivo, responsavel }) {
  if (!PAYMENT[status]) return { error: 'Status de pagamento inválido.' };
  if (!motivo || !motivo.trim()) return { error: 'Motivo é obrigatório para alteração manual.' };
  if (!responsavel || !responsavel.trim()) return { error: 'Usuário responsável é obrigatório.' };
  const db = readOrders();
  const o = db.orders.find(x => x.id === id);
  if (!o) return { error: 'Pedido não encontrado.' };
  const from = PAYMENT[o.payment.status];
  const t = stamp();
  o.payment.status = status;
  o.payment.confirmation = { source: 'Alteração manual (exceção)', transactionId: '—', statusReturned: status,
    responsavel: responsavel.trim(), motivo: motivo.trim(), data: t.data, hora: t.hora, at: t.iso };
  addLog(o, { field: 'pagamento', from, to: PAYMENT[status], user: responsavel.trim(), origin: 'MANUAL', reason: motivo.trim() });
  if (status === 'aprovado' && !o.fulfillment) {
    const prod = getProduct(o.productSku) || defaultProduct();
    const v = getVariant(prod, o.variantId);
    o.costs.custoFornecedor = num(v.custoFornecedor);
    o.costs.outrosCustos = num(prod.outrosCustos);
    o.costs.margemEstimada = Number((o.costs.valorPago - o.costs.custoFornecedor - o.costs.outrosCustos).toFixed(2));
    o.costs.aprovadoEm = t.iso;
    o.supplier.fornecedor = prod.fornecedor || '';
    o.supplier.linkProduto = prod.linkFornecedor || '';
    o.fulfillment = 'aguardando_compra';
    addLog(o, { field: 'operacao', from: '—', to: 'Aguardando compra do fornecedor', user: 'Sistema', origin: 'AUTOMÁTICA' });
  }
  writeOrders(db);
  return { order: o };
}

/* Avanço simples (aguardar_envio / acompanhar / entregue / finalizar) */
function advance(id, actionKey, user) {
  const db = readOrders();
  const o = db.orders.find(x => x.id === id);
  if (!o) return { error: 'Pedido não encontrado.' };
  const action = getAction(actionKey);
  if (!action) return { error: 'Ação inválida.' };
  if (paymentBlocked(o)) return { error: 'Pagamento ' + o.payment.status + ': operação bloqueada.' };
  if (o.payment.status !== 'aprovado') return { error: 'AGUARDANDO CONFIRMAÇÃO DO PAGAMENTO.' };
  if (!action.can(o)) return { error: 'Esta etapa ainda não pode ser executada.' };
  const before = action.field === 'operacao' ? FULFILLMENT[o.fulfillment]
    : action.field === 'envio' ? SHIPPING[o.shippingStatus] : 'Em andamento';
  action.apply(o);
  addLog(o, { field: action.field, from: before, to: action.to, user: user || 'Administrador', origin: 'MANUAL' });
  writeOrders(db);
  return { order: o };
}

/* Registrar a COMPRA no fornecedor → COMPRA REALIZADA (recalcula margem real) */
function registrarCompra(id, data, user) {
  const db = readOrders();
  const o = db.orders.find(x => x.id === id);
  if (!o) return { error: 'Pedido não encontrado.' };
  if (o.payment.status !== 'aprovado') return { error: 'AGUARDANDO CONFIRMAÇÃO DO PAGAMENTO.' };
  if (o.fulfillment !== 'aguardando_compra') return { error: 'Este pedido não está aguardando compra.' };

  o.supplier.pedidoFornecedor = String(data.pedidoFornecedor || '').trim();
  o.supplier.valorPagoFornecedor = num(data.valorPagoFornecedor);
  o.supplier.dataCompra = String(data.dataCompra || '').trim() || stamp().data + ' ' + stamp().hora;
  o.supplier.fornecedor = String(data.fornecedor || o.supplier.fornecedor || '').trim();
  o.supplier.observacoes = String(data.observacoes || '').trim();
  o.supplier.comprovante = String(data.comprovante || '').trim();

  o.costs.custoReal = o.supplier.valorPagoFornecedor;
  o.costs.margemOperacional = Number((o.costs.valorPago - o.costs.custoReal - o.costs.outrosCustos).toFixed(2));

  o.fulfillment = 'compra_realizada';
  addLog(o, { field: 'operacao', from: 'Aguardando compra do fornecedor', to: 'Compra realizada',
    user: user || 'Administrador', origin: 'MANUAL',
    reason: `Pedido fornecedor ${o.supplier.pedidoFornecedor || '—'} · pago R$ ${(o.costs.custoReal||0).toFixed(2)} · margem op. R$ ${(o.costs.margemOperacional||0).toFixed(2)}` });
  writeOrders(db);
  return { order: o };
}

/* Registrar rastreio e marcar ENVIADO (sai da fila de compra → entra em acompanhamento depois) */
function registrarEnvio(id, data, user) {
  const db = readOrders();
  const o = db.orders.find(x => x.id === id);
  if (!o) return { error: 'Pedido não encontrado.' };
  if (o.payment.status !== 'aprovado') return { error: 'AGUARDANDO CONFIRMAÇÃO DO PAGAMENTO.' };
  if (o.fulfillment !== 'aguardando_envio') return { error: 'Este pedido não está aguardando envio.' };
  o.tracking.codigo = String(data.codigo || '').trim();
  o.tracking.transportadora = String(data.transportadora || '').trim();
  o.tracking.dataPostagem = String(data.dataPostagem || '').trim();
  o.tracking.link = String(data.link || '').trim();
  o.shippingStatus = 'enviado';
  addLog(o, { field: 'envio', from: 'Aguardando envio do fornecedor', to: 'Enviado',
    user: user || 'Administrador', origin: 'MANUAL',
    reason: o.tracking.codigo ? `Rastreio ${o.tracking.transportadora || ''} ${o.tracking.codigo}` : 'Sem código de rastreio' });
  writeOrders(db);
  return { order: o };
}

/* ===================== dashboard / fila ===================== */
function dashboard() {
  const orders = readOrders().orders;
  const c = { recebidos: orders.length, pgto_pendente: 0, pgto_processando: 0, pgto_aprovado: 0,
    aguardando_compra: 0, compra_realizada: 0, aguardando_envio: 0, em_acompanhamento: 0, entregues: 0, finalizados: 0 };
  for (const o of orders) {
    if (o.finalizado) { c.finalizados++; continue; }
    if (o.payment.status === 'pendente') c.pgto_pendente++;
    if (o.payment.status === 'em_processamento') c.pgto_processando++;
    if (o.payment.status === 'aprovado') c.pgto_aprovado++;
    if (o.fulfillment === 'aguardando_compra') c.aguardando_compra++;
    if (o.fulfillment === 'compra_realizada') c.compra_realizada++;
    if (o.fulfillment === 'aguardando_envio') c.aguardando_envio++;
    if (['enviado', 'acompanhamento'].includes(o.shippingStatus)) c.em_acompanhamento++;
    if (o.shippingStatus === 'entregue') c.entregues++;
  }
  return c;
}
function actionQueue() {
  const orders = readOrders().orders.filter(o => !o.finalizado);
  return {
    verificar_pgto: orders.filter(o => ['pendente', 'em_processamento'].includes(o.payment.status)).length,
    comprar_fornecedor: orders.filter(o => o.fulfillment === 'aguardando_compra').length,
    aguardando_envio: orders.filter(o => o.fulfillment === 'aguardando_envio').length,
    em_acompanhamento: orders.filter(o => ['enviado', 'acompanhamento'].includes(o.shippingStatus)).length
  };
}

/* ===================== VISÃO DO CLIENTE (sem custo/margem/link do fornecedor) ===================== */
function clientView(o) {
  const stageLabel = o.finalizado ? 'Finalizado' : FLOW_STAGES[stageIndex(o) - 1];
  // mapeia estágios internos para uma linguagem simples ao cliente
  const publicStatus =
    o.finalizado ? 'Concluído'
    : o.shippingStatus === 'entregue' ? 'Entregue'
    : ['enviado', 'acompanhamento'].includes(o.shippingStatus) ? 'A caminho'
    : o.payment.status === 'aprovado' ? 'Pagamento aprovado — preparando envio'
    : o.payment.status === 'pendente' ? 'Aguardando pagamento'
    : PAYMENT[o.payment.status] || 'Em processamento';
  return {
    ref: o.ref,
    status: publicStatus,
    etapa: stageLabel,
    itens: o.items.map(i => ({ produto: i.title, variacao: i.variacao, quantidade: i.quantity })),
    total: o.total,
    entrega: {
      cidade: o.shipping.cidade, estado: o.shipping.estado,
      // rastreio só quando existir
      rastreio: o.tracking.codigo || null, transportadora: o.tracking.transportadora || null, link: o.tracking.link || null
    }
    // NUNCA: costs, supplier, linkFornecedor, margem
  };
}

module.exports = {
  PAYMENT, FULFILLMENT, SHIPPING, FLOW_STAGES, ACTIONS,
  stageIndex, nextStep, paymentBlocked, margemVariante, getVariant,
  lookupCep, buildShipping,
  listProducts, getProduct, updateProduct,
  createOrder, updateOrder, getOrder, listOrders,
  advance, registrarCompra, registrarEnvio, setPaymentFromProvider, overridePayment,
  dashboard, actionQueue, clientView
};
