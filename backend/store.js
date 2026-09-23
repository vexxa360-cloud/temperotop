/**
 * Store de pedidos + ciclo de vida (pagamento / operação / envio) com auditoria.
 * -------------------------------------------------------------------------
 * Persistência simples em JSON (backend/data/orders.json). Para produção com
 * volume, troque por um banco mantendo as mesmas funções exportadas.
 *
 * REGRA FUNDAMENTAL (spec #70): pagamento, operação e envio são campos
 * INDEPENDENTES. O "estágio atual" da barra de progresso é DERIVADO deles.
 */
const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, 'data');
const ORDERS_FILE = path.join(DATA_DIR, 'orders.json');

/* ===================== enums / rótulos ===================== */
const PAYMENT = {
  pendente:         'Pagamento pendente',
  em_processamento: 'Pagamento em processamento',
  aprovado:         'Pagamento aprovado',
  rejeitado:        'Pagamento rejeitado',
  cancelado:        'Pagamento cancelado',
  reembolsado:      'Pagamento reembolsado'
};
const OPERATION = {
  aguardando:   'Aguardando faturamento',
  faturado:     'Faturado',
  separacao:    'Em separação',
  pronto_envio: 'Pronto para envio'
};
const SHIPPING = {
  aguardando:   'Aguardando envio',
  enviado:      'Enviado',
  acompanhamento:'Em acompanhamento',
  em_transito:  'Em trânsito',
  saiu_entrega: 'Saiu para entrega',
  entregue:     'Entregue'
};

/* Mapeia status oficial do Mercado Pago -> nosso status de pagamento */
const MP_TO_PAYMENT = {
  pending: 'pendente',
  in_process: 'em_processamento',
  authorized: 'em_processamento',
  approved: 'aprovado',
  rejected: 'rejeitado',
  cancelled: 'cancelado',
  refunded: 'reembolsado',
  charged_back: 'reembolsado'
};

/* Fluxo mestre (spec #69) — usado só para a barra de progresso (derivado) */
const FLOW_STAGES = [
  'Pedido recebido',
  'Pagamento pendente',
  'Pagamento em processamento',
  'Pagamento aprovado',
  'Faturamento',
  'Separação',
  'Pronto para envio',
  'Enviado',
  'Acompanhamento',
  'Em trânsito',
  'Saiu para entrega',
  'Entregue',
  'Finalizado'
];

/* Índice (1-based) do estágio ATUAL, derivado dos 3 status independentes */
function stageIndex(o) {
  if (o.finalizado) return 13;
  const s = o.shippingStatus, op = o.operation, p = o.payment.status;
  if (s === 'entregue') return 12;
  if (s === 'saiu_entrega') return 11;
  if (s === 'em_transito') return 10;
  if (s === 'acompanhamento') return 9;
  if (s === 'enviado') return 8;
  if (op === 'pronto_envio') return 7;
  if (op === 'separacao') return 6;
  if (op === 'faturado') return 5;
  if (p === 'aprovado') return 4;
  if (p === 'em_processamento') return 3;
  if (p === 'pendente') return 2;
  return 1;
}
const paymentBlocked = o => ['rejeitado', 'cancelado', 'reembolsado'].includes(o.payment.status);

/* ===================== ações operacionais (spec #64/#66) ===================== */
/* Cada ação só habilita quando a anterior foi concluída e o pagamento aprovado. */
const ACTIONS = [
  { key: 'faturar',   label: 'Confirmar Faturamento',      field: 'operacao', to: 'Faturado',
    can: o => o.payment.status === 'aprovado' && o.operation === 'aguardando',
    apply: o => { o.operation = 'faturado'; } },
  { key: 'separar',   label: 'Iniciar Separação',          field: 'operacao', to: 'Separação',
    can: o => o.operation === 'faturado',
    apply: o => { o.operation = 'separacao'; } },
  { key: 'pronto',    label: 'Marcar Pronto para Envio',   field: 'operacao', to: 'Pronto para envio',
    can: o => o.operation === 'separacao',
    apply: o => { o.operation = 'pronto_envio'; } },
  { key: 'enviar',    label: 'Marcar como Enviado',        field: 'envio', to: 'Enviado',
    can: o => o.operation === 'pronto_envio' && o.shippingStatus === 'aguardando',
    apply: o => { o.shippingStatus = 'enviado'; } },
  { key: 'acompanhar',label: 'Enviar para Acompanhamento', field: 'envio', to: 'Acompanhamento',
    can: o => o.shippingStatus === 'enviado',
    apply: o => { o.shippingStatus = 'acompanhamento'; o.tracking = 'ativo'; } },
  { key: 'transito',  label: 'Marcar Em Trânsito',         field: 'envio', to: 'Em trânsito',
    can: o => o.shippingStatus === 'acompanhamento',
    apply: o => { o.shippingStatus = 'em_transito'; } },
  { key: 'saiu',      label: 'Saiu para Entrega',          field: 'envio', to: 'Saiu para entrega',
    can: o => o.shippingStatus === 'em_transito',
    apply: o => { o.shippingStatus = 'saiu_entrega'; } },
  { key: 'entregue',  label: 'Marcar como Entregue',       field: 'envio', to: 'Entregue',
    can: o => o.shippingStatus === 'saiu_entrega',
    apply: o => { o.shippingStatus = 'entregue'; } },
  { key: 'finalizar', label: 'Finalizar Pedido',           field: 'pedido', to: 'Finalizado',
    can: o => o.shippingStatus === 'entregue' && !o.finalizado,
    apply: o => { o.finalizado = true; } }
];
const getAction = key => ACTIONS.find(a => a.key === key);
const nextAction = o => (paymentBlocked(o) ? null : ACTIONS.find(a => a.can(o)) || null);

/* ===================== persistência ===================== */
function ensure() {
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
  if (!fs.existsSync(ORDERS_FILE)) fs.writeFileSync(ORDERS_FILE, JSON.stringify({ seq: 0, orders: [] }, null, 2));
}
function readAll() {
  ensure();
  try { return JSON.parse(fs.readFileSync(ORDERS_FILE, 'utf8')); } catch { return { seq: 0, orders: [] }; }
}
function writeAll(db) { ensure(); fs.writeFileSync(ORDERS_FILE, JSON.stringify(db, null, 2)); }

const onlyDigits = s => String(s || '').replace(/\D/g, '');
function stamp() {
  const d = new Date();
  return {
    iso: d.toISOString(),
    data: d.toLocaleDateString('pt-BR'),
    hora: d.toLocaleTimeString('pt-BR', { hour12: false })
  };
}
function addLog(o, { field, from, to, user, origin, reason }) {
  const t = stamp();
  o.logs.unshift({ at: t.iso, data: t.data, hora: t.hora, field, from, to, user, origin, reason: reason || '' });
}

/* ===================== CEP (ViaCEP, no servidor) ===================== */
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
      logradouro: d.logradouro || '', bairro: d.bairro || '',
      cidade: d.localidade || '', estado: d.uf || ''
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
    cep: base.cep,
    logradouro: base.logradouro || cs.endereco || '',
    numero: String(cs.numero || '').trim(),
    complemento: String(cs.complemento || '').trim(),
    bairro: base.bairro || cs.bairro || '',
    cidade: base.cidade || cs.cidade || '',
    estado: base.estado || cs.estado || '',
    cep_validado: r.ok,
    cep_status: r.ok ? 'validado' : r.reason
  };
}

/* ===================== pedidos ===================== */
function createOrder({ payer, shipping, items }) {
  const db = readAll();
  db.seq += 1;
  const number = String(db.seq).padStart(6, '0');
  const total = items.reduce((s, i) => s + Number(i.unit_price) * (Number(i.quantity) || 1), 0);
  const t = stamp();

  const order = {
    id: number, ref: `PEDIDO #${number}`, createdAt: t.iso,
    customer: {
      nome: payer.name || '', email: payer.email || '',
      telefone: payer.phone || '', cpf: payer.identification?.number || ''
    },
    shipping,
    items: items.map(i => ({ title: i.title, quantity: Number(i.quantity) || 1, unit_price: Number(i.unit_price) })),
    total,
    /* --- três status independentes (spec #70) --- */
    payment: { provider: 'mercadopago', preferenceId: null, status: 'pendente', confirmation: null },
    operation: 'aguardando',
    shippingStatus: 'aguardando',
    tracking: 'inativo',
    finalizado: false,
    logs: []
  };
  addLog(order, { field: 'pedido', from: '—', to: 'Pedido recebido', user: 'Sistema', origin: 'AUTOMÁTICA' });
  addLog(order, { field: 'pagamento', from: '—', to: 'Pagamento pendente', user: 'Sistema', origin: 'AUTOMÁTICA' });

  db.orders.unshift(order);
  writeAll(db);
  return order;
}

function updateOrder(id, patch) {
  const db = readAll();
  const o = db.orders.find(x => x.id === id);
  if (!o) return null;
  Object.assign(o, patch);
  writeAll(db);
  return o;
}

/* Avança uma etapa operacional/envio (manual, pelo admin) — spec #63/#64/#65 */
function advance(id, actionKey, user) {
  const db = readAll();
  const o = db.orders.find(x => x.id === id);
  if (!o) return { error: 'Pedido não encontrado.' };
  const action = getAction(actionKey);
  if (!action) return { error: 'Ação inválida.' };
  if (paymentBlocked(o)) return { error: 'Pagamento ' + o.payment.status + ': etapas operacionais bloqueadas.' };
  if (o.payment.status !== 'aprovado')
    return { error: 'AGUARDANDO CONFIRMAÇÃO DO PAGAMENTO.' };   // spec #63
  if (!action.can(o)) return { error: 'Esta etapa ainda não pode ser executada.' };

  const before = action.field === 'operacao' ? OPERATION[o.operation]
    : action.field === 'envio' ? SHIPPING[o.shippingStatus]
    : (o.finalizado ? 'Finalizado' : 'Em andamento');
  action.apply(o);
  addLog(o, { field: action.field, from: before, to: action.to, user: user || 'Administrador', origin: 'MANUAL' });
  writeAll(db);
  return { order: o };
}

/* Atualiza pagamento AUTOMATICAMENTE a partir do Mercado Pago — spec #61/#62 */
function setPaymentFromProvider(id, mpStatus, meta = {}) {
  const db = readAll();
  const o = db.orders.find(x => x.id === id);
  if (!o) return { error: 'Pedido não encontrado.' };
  const status = MP_TO_PAYMENT[mpStatus] || 'em_processamento';
  const from = PAYMENT[o.payment.status];
  const t = stamp();
  o.payment.status = status;
  o.payment.confirmation = {
    source: meta.source || 'Mercado Pago / Webhook',
    transactionId: meta.transactionId || '',
    statusReturned: mpStatus,
    data: t.data, hora: t.hora, at: t.iso
  };
  addLog(o, { field: 'pagamento', from, to: PAYMENT[status], user: 'Mercado Pago', origin: 'AUTOMÁTICA',
    reason: `Transação ${meta.transactionId || '—'} · status "${mpStatus}"` });
  writeAll(db);
  return { order: o };
}

/* Alteração MANUAL EXCEPCIONAL de pagamento — exige motivo + responsável (spec #62) */
function overridePayment(id, status, { motivo, responsavel }) {
  if (!PAYMENT[status]) return { error: 'Status de pagamento inválido.' };
  if (!motivo || !motivo.trim()) return { error: 'Motivo é obrigatório para alteração manual.' };
  if (!responsavel || !responsavel.trim()) return { error: 'Usuário responsável é obrigatório.' };
  const db = readAll();
  const o = db.orders.find(x => x.id === id);
  if (!o) return { error: 'Pedido não encontrado.' };
  const from = PAYMENT[o.payment.status];
  const t = stamp();
  o.payment.status = status;
  o.payment.confirmation = {
    source: 'Alteração manual (exceção)', transactionId: '—',
    statusReturned: status, responsavel: responsavel.trim(), motivo: motivo.trim(),
    data: t.data, hora: t.hora, at: t.iso
  };
  addLog(o, { field: 'pagamento', from, to: PAYMENT[status], user: responsavel.trim(),
    origin: 'MANUAL', reason: motivo.trim() });
  writeAll(db);
  return { order: o };
}

/* ===================== dashboard / fila (spec #67/#68) ===================== */
function dashboard() {
  const orders = readAll().orders;
  const c = {
    recebidos: orders.length,
    pgto_pendente: 0, pgto_processando: 0, pgto_aprovado: 0,
    aguardando_faturamento: 0, em_separacao: 0, prontos_envio: 0,
    em_acompanhamento: 0, entregues: 0, finalizados: 0
  };
  for (const o of orders) {
    if (o.finalizado) { c.finalizados++; continue; }
    if (o.payment.status === 'pendente') c.pgto_pendente++;
    if (o.payment.status === 'em_processamento') c.pgto_processando++;
    if (o.payment.status === 'aprovado') c.pgto_aprovado++;
    if (o.payment.status === 'aprovado' && o.operation === 'aguardando') c.aguardando_faturamento++;
    if (o.operation === 'separacao') c.em_separacao++;
    if (o.operation === 'pronto_envio') c.prontos_envio++;
    if (['acompanhamento', 'em_transito', 'saiu_entrega'].includes(o.shippingStatus)) c.em_acompanhamento++;
    if (o.shippingStatus === 'entregue') c.entregues++;
  }
  return c;
}
function actionQueue() {
  const orders = readAll().orders.filter(o => !o.finalizado);
  return {
    verificar_pgto: orders.filter(o => ['pendente', 'em_processamento'].includes(o.payment.status)).length,
    aguardando_faturamento: orders.filter(o => o.payment.status === 'aprovado' && o.operation === 'aguardando').length,
    aguardando_separacao: orders.filter(o => o.operation === 'faturado').length,
    aguardando_envio: orders.filter(o => o.operation === 'pronto_envio').length,
    em_acompanhamento: orders.filter(o => ['acompanhamento', 'em_transito', 'saiu_entrega'].includes(o.shippingStatus)).length
  };
}

const getOrder = id => readAll().orders.find(o => o.id === id) || null;
const listOrders = () => readAll().orders;

module.exports = {
  PAYMENT, OPERATION, SHIPPING, FLOW_STAGES, ACTIONS,
  stageIndex, nextAction, paymentBlocked,
  lookupCep, buildShipping,
  createOrder, updateOrder, getOrder, listOrders,
  advance, setPaymentFromProvider, overridePayment,
  dashboard, actionQueue
};
