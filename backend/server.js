/**
 * Backend TemperoTop — Checkout + Mercado Pago + Ciclo de Pedido
 * -------------------------------------------------------------
 * Público:
 *   POST /api/cep/:cep            → valida CEP (ViaCEP) no servidor
 *   POST /api/create-preference   → valida, cria PEDIDO e a preferência MP
 *   POST /api/webhook/mercadopago → recebe eventos e AVANÇA o pagamento sozinho
 * Admin (protegido por token):
 *   GET  /admin                       → dashboard (contadores + fila de ações)
 *   GET  /admin/orders/:id            → pedido: progresso + painel de avanço + log
 *   POST /admin/orders/:id/advance    → avança etapa operacional/envio (manual)
 *   POST /admin/orders/:id/payment    → alteração manual EXCEPCIONAL de pagamento
 *
 * Credenciais só no .env (veja .env.example).
 */
require('dotenv').config();
const express = require('express');
const path = require('path');
const store = require('./store');
let MercadoPagoConfig, Preference, Payment;
try { ({ MercadoPagoConfig, Preference, Payment } = require('mercadopago')); } catch { /* npm install */ }

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, '..')));

const ACCESS_TOKEN = process.env.MP_ACCESS_TOKEN;
const PAYMENT_LINK = (process.env.MP_PAYMENT_LINK || '').trim(); // link de pagamento pronto do MP
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || '';
const PORT = process.env.PORT || 3000;
const BASE_URL = process.env.BASE_URL || `http://localhost:${PORT}`;

const onlyDigits = s => String(s || '').replace(/\D/g, '');
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));
const brl = n => 'R$ ' + Number(n).toFixed(2).replace('.', ',');

/* ==================== CEP ==================== */
app.get('/api/cep/:cep', async (req, res) => {
  const r = await store.lookupCep(req.params.cep);
  if (r.ok) return res.json(r.data);
  const map = {
    invalid:     { code: 400, msg: 'CEP inválido. Informe 8 dígitos.' },
    not_found:   { code: 404, msg: 'CEP não encontrado. Verifique o número informado.' },
    unavailable: { code: 503, msg: 'Não foi possível consultar o CEP agora. Preencha o endereço manualmente.' }
  };
  const e = map[r.reason] || map.unavailable;
  res.status(e.code).json({ error: e.msg, reason: r.reason });
});

/* ==================== Criar pedido + preferência ==================== */
const PUBLIC_KEY = (process.env.MP_PUBLIC_KEY || '').trim();
const PAYMENT_ENABLED = !!(ACCESS_TOKEN && Payment); // pagamento no site exige a API

/* Public Key para o frontend inicializar o Bricks (não é segredo) */
app.get('/api/config', (req, res) => {
  res.json({ publicKey: PUBLIC_KEY, paymentEnabled: PAYMENT_ENABLED });
});

/* Etapa 1: valida dados, revalida CEP e cria o PEDIDO (sem cobrar ainda) */
app.post('/api/create-order', async (req, res) => {
  try {
    const { items = [], payer = {}, shipping = {} } = req.body;
    const errors = [];
    if (!Array.isArray(items) || !items.length) errors.push('Carrinho vazio.');
    if (!payer.name) errors.push('Nome é obrigatório.');
    if (!payer.email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(payer.email)) errors.push('E-mail inválido.');
    if (onlyDigits(payer.identification?.number).length !== 11) errors.push('CPF inválido.');
    if (onlyDigits(payer.phone).length < 10) errors.push('Telefone inválido.');
    if (onlyDigits(shipping.cep).length !== 8) errors.push('CEP inválido.');
    if (!String(shipping.numero || '').trim()) errors.push('Número é obrigatório.');
    if (errors.length) return res.status(400).json({ error: errors.join(' ') });

    const finalShipping = await store.buildShipping(shipping);
    if (!finalShipping.logradouro || !finalShipping.cidade || !finalShipping.estado)
      return res.status(400).json({ error: 'Endereço incompleto. Verifique o CEP e os campos.' });

    const order = store.createOrder({ payer, shipping: finalShipping, items });
    res.json({ orderId: order.id, ref: order.ref, amount: order.total, payment_enabled: PAYMENT_ENABLED });
  } catch (err) {
    console.error('Erro ao criar pedido:', err);
    res.status(500).json({ error: 'Não foi possível registrar o pedido agora. Tente novamente.' });
  }
});

/* Etapa 2: processa o pagamento (Checkout Transparente / Bricks) — dentro do site */
app.post('/api/process-payment', async (req, res) => {
  try {
    if (!PAYMENT_ENABLED) return res.status(503).json({ error: 'Pagamento não configurado no servidor (MP_ACCESS_TOKEN).' });
    const { orderId, formData } = req.body;
    const order = store.getOrder(orderId);
    if (!order) return res.status(404).json({ error: 'Pedido não encontrado.' });
    if (!formData || !formData.payment_method_id) return res.status(400).json({ error: 'Dados de pagamento inválidos.' });

    const client = new MercadoPagoConfig({ accessToken: ACCESS_TOKEN });
    const payment = new Payment(client);

    // O valor é definido no SERVIDOR (nunca confia no valor vindo do navegador)
    const body = {
      transaction_amount: Number(order.total),
      description: 'Porta-Temperos Giratório 360°',
      external_reference: order.id,
      payment_method_id: formData.payment_method_id,
      payer: {
        email: formData.payer?.email || order.customer.email,
        identification: formData.payer?.identification || { type: 'CPF', number: onlyDigits(order.customer.cpf) }
      }
    };
    if (formData.token) body.token = formData.token;                     // cartão
    if (formData.installments) body.installments = Number(formData.installments);
    if (formData.issuer_id) body.issuer_id = formData.issuer_id;

    const result = await payment.create({
      body,
      requestOptions: { idempotencyKey: `${order.id}-${Date.now()}` }
    });

    // Atualiza o pedido automaticamente com o status retornado
    store.setPaymentFromProvider(order.id, result.status, {
      source: 'Mercado Pago / API', transactionId: String(result.id)
    });

    const tx = result.point_of_interaction?.transaction_data || {};
    res.json({
      status: result.status,                 // approved | in_process | pending | rejected
      status_detail: result.status_detail,
      status_detail_msg: statusDetailMsg(result.status_detail),
      payment_id: result.id,
      qr_code: tx.qr_code || null,           // Pix copia-e-cola
      qr_code_base64: tx.qr_code_base64 || null
    });
  } catch (err) {
    console.error('Erro ao processar pagamento:', err?.message || err);
    res.status(400).json({ error: 'Não foi possível processar o pagamento. Verifique os dados e tente novamente.' });
  }
});

function statusDetailMsg(detail) {
  const m = {
    cc_rejected_insufficient_amount: 'Saldo/limite insuficiente.',
    cc_rejected_bad_filled_card_number: 'Número do cartão inválido.',
    cc_rejected_bad_filled_date: 'Data de validade inválida.',
    cc_rejected_bad_filled_security_code: 'Código de segurança inválido.',
    cc_rejected_high_risk: 'Pagamento recusado por segurança. Tente outro método.',
    cc_rejected_call_for_authorize: 'Autorize o pagamento com seu banco e tente de novo.'
  };
  return m[detail] || '';
}

/* ==================== Webhook Mercado Pago (avanço automático) ==================== */
app.post('/api/webhook/mercadopago', async (req, res) => {
  res.sendStatus(200); // responde rápido; processa depois
  try {
    // Modo de teste local (sem credenciais): aceita { orderId, status }
    if ((!ACCESS_TOKEN || !Payment) && req.body && req.body.orderId && req.body.status) {
      store.setPaymentFromProvider(req.body.orderId, req.body.status,
        { source: 'Mercado Pago / Webhook (teste)', transactionId: req.body.transactionId || 'TESTE' });
      return;
    }
    const type = req.query.type || req.body?.type;
    const paymentId = req.query['data.id'] || req.body?.data?.id;
    if (type !== 'payment' || !paymentId || !ACCESS_TOKEN || !Payment) return;

    const client = new MercadoPagoConfig({ accessToken: ACCESS_TOKEN });
    const info = await new Payment(client).get({ id: paymentId });
    const orderId = info.external_reference;
    if (!orderId) return;
    store.setPaymentFromProvider(orderId, info.status, {
      source: 'Mercado Pago / Webhook', transactionId: String(info.id)
    });
    console.log(`🔔 Webhook: pedido #${orderId} → pagamento "${info.status}"`);
  } catch (err) { console.error('Erro no webhook MP:', err); }
});

/* ==================== Painel administrativo ==================== */
function adminAuth(req, res, next) {
  const token = req.query.token || req.body?.token || req.headers['x-admin-token'];
  const isLocal = ['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(req.ip);
  if (ADMIN_TOKEN ? token === ADMIN_TOKEN : isLocal) return next();
  res.status(401).send('<h1>401 — Acesso restrito</h1><p>Informe ?token=SEU_ADMIN_TOKEN</p>');
}
const q = req => (req.query.token ? `?token=${encodeURIComponent(req.query.token)}` : '');
const tokenField = req => (req.query.token ? `<input type="hidden" name="token" value="${esc(req.query.token)}">` : '');

const CSS = `:root{--o:#ea9a2e;--ink:#1c1a17;--line:#e7e2d8;--muted:#6b6459;--ok:#2e7d32;--wait:#b7791f;--bad:#c0392b}
*{box-sizing:border-box}body{font:15px/1.55 system-ui,Segoe UI,Roboto,sans-serif;color:var(--ink);margin:0;background:#f4f1ea}
.wrap{max-width:1060px;margin:0 auto;padding:24px}
h1{margin:0 0 4px}.sub{color:var(--muted);margin:0 0 22px}
a{color:#0a58ca;text-decoration:none}a:hover{text-decoration:underline}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:11px 13px;border-bottom:1px solid var(--line);font-size:14px}
th{background:#efe9df;font-weight:700}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:700;white-space:nowrap}
.b-ok{background:#d1e7dd;color:#0f5132}.b-wait{background:#fff3cd;color:#8a6d00}.b-bad{background:#f8d7da;color:#842029}.b-info{background:#cfe2ff;color:#084298}.b-mut{background:#e9ecef;color:#495057}
.grid{display:grid;gap:14px}.cards{grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.stat b{display:block;font-size:28px;line-height:1.1}.stat span{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.04em}
.h2{margin:26px 0 12px;font-size:17px}
.kv{display:grid;grid-template-columns:150px 1fr;gap:6px 12px}.kv b{color:var(--muted);font-weight:600}
.btn{display:inline-block;background:var(--o);color:#fff;padding:10px 18px;border:none;border-radius:8px;font-weight:700;cursor:pointer;font-size:14px}
.btn:hover{background:#d1841c}.btn.sm{padding:6px 12px;font-size:13px}.btn.ghost{background:#fff;color:var(--ink);border:1px solid var(--line)}
.queue li{margin:6px 0}.queue .dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:8px}
/* progress */
.prog{list-style:none;margin:0;padding:0}
.prog li{display:flex;align-items:center;gap:12px;padding:5px 0;color:var(--muted)}
.prog .mk{width:24px;height:24px;border-radius:50%;border:2px solid #cfc7b8;display:grid;place-items:center;font-size:13px;flex-shrink:0;background:#fff}
.prog li.done{color:var(--ink)}.prog li.done .mk{background:var(--ok);border-color:var(--ok);color:#fff}
.prog li.cur{color:var(--ink);font-weight:800}.prog li.cur .mk{background:var(--o);border-color:var(--o);color:#fff;box-shadow:0 0 0 4px rgba(234,154,46,.25)}
.status-row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}
.panel{background:#fff8ee;border:1px solid #f0dcb8;border-radius:12px;padding:18px;margin:12px 0}
.panel .cur{font-size:20px;font-weight:800}
details{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin-top:14px}
summary{cursor:pointer;font-weight:700}
label{display:block;font-size:13px;font-weight:600;color:var(--muted);margin:10px 0 4px}
input,select{font:inherit;padding:9px 11px;border:1px solid var(--line);border-radius:8px;width:100%;max-width:360px}
.small{font-size:12px;color:var(--muted)}`;

const page = (title, inner) => `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)}</title><style>${CSS}</style></head>
<body><div class="wrap">${inner}</div></body></html>`;

/* badges dos 3 status independentes */
function payBadge(s){
  const m={aprovado:['b-ok','Aprovado'],pendente:['b-wait','Pendente'],em_processamento:['b-info','Em processamento'],
    rejeitado:['b-bad','Rejeitado'],cancelado:['b-bad','Cancelado'],reembolsado:['b-mut','Reembolsado']};
  const [c,l]=m[s]||['b-mut',s]; return `<span class="badge ${c}">💳 ${l}</span>`;
}
const opBadge = s => `<span class="badge b-info">📦 ${esc(store.OPERATION[s])}</span>`;
const shipBadge = s => `<span class="badge ${s==='entregue'?'b-ok':s==='aguardando'?'b-mut':'b-info'}">🚚 ${esc(store.SHIPPING[s])}</span>`;

function renderProgress(o){
  const cur = store.stageIndex(o);
  return `<ul class="prog">${store.FLOW_STAGES.map((label,i)=>{
    const n=i+1; const cls = n<cur?'done':n===cur?'cur':'';
    const mk = n<cur?'✓':n===cur?'●':'○';
    return `<li class="${cls}"><span class="mk">${mk}</span>${esc(label)}</li>`;
  }).join('')}</ul>`;
}

/* ---- Dashboard (spec #67 + #68) ---- */
app.get('/admin', adminAuth, (req, res) => {
  const c = store.dashboard(); const Q = store.actionQueue(); const orders = store.listOrders();
  const stat = (label,val)=>`<div class="card stat"><b>${val}</b><span>${label}</span></div>`;
  const rows = orders.map(o=>`<tr>
    <td><a href="/admin/orders/${o.id}${q(req)}">${esc(o.ref)}</a></td>
    <td>${esc(o.customer.nome)}</td>
    <td>${payBadge(o.payment.status)}</td>
    <td>${o.finalizado?'<span class="badge b-ok">✓ Finalizado</span>':esc(store.FLOW_STAGES[store.stageIndex(o)-1])}</td>
    <td>${brl(o.total)}</td>
  </tr>`).join('') || '<tr><td colspan="5">Nenhum pedido ainda.</td></tr>';

  res.send(page('Painel — TemperoTop', `
    <h1>Painel de Pedidos</h1><p class="sub">Visão em tempo real do ciclo de cada pedido</p>

    <div class="grid cards">
      ${stat('Pedidos recebidos', c.recebidos)}
      ${stat('Pagamentos pendentes', c.pgto_pendente)}
      ${stat('Em processamento', c.pgto_processando)}
      ${stat('Pagamentos aprovados', c.pgto_aprovado)}
      ${stat('Aguardando faturamento', c.aguardando_faturamento)}
      ${stat('Em separação', c.em_separacao)}
      ${stat('Prontos para envio', c.prontos_envio)}
      ${stat('Em acompanhamento', c.em_acompanhamento)}
      ${stat('Entregues', c.entregues)}
      ${stat('Finalizados', c.finalizados)}
    </div>

    <h2 class="h2">Próximas ações</h2>
    <div class="card"><ul class="queue" style="list-style:none;padding:0;margin:0">
      <li><span class="dot" style="background:#c0392b"></span><b>${Q.verificar_pgto}</b> pagamento(s) para verificar</li>
      <li><span class="dot" style="background:#e08e0b"></span><b>${Q.aguardando_faturamento}</b> aguardando faturamento</li>
      <li><span class="dot" style="background:#e0c40b"></span><b>${Q.aguardando_separacao}</b> aguardando separação</li>
      <li><span class="dot" style="background:#0a84ff"></span><b>${Q.aguardando_envio}</b> aguardando envio</li>
      <li><span class="dot" style="background:#2e7d32"></span><b>${Q.em_acompanhamento}</b> em acompanhamento</li>
    </ul></div>

    <h2 class="h2">Todos os pedidos</h2>
    <table><thead><tr><th>Pedido</th><th>Cliente</th><th>Pagamento</th><th>Etapa atual</th><th>Total</th></tr></thead>
    <tbody>${rows}</tbody></table>`));
});

/* ---- Detalhe do pedido ---- */
app.get('/admin/orders/:id', adminAuth, (req, res) => {
  const o = store.getOrder(req.params.id);
  if (!o) return res.status(404).send(page('Não encontrado', '<h1>Pedido não encontrado</h1>'));
  const s = o.shipping, cf = o.payment.confirmation, na = store.nextAction(o);

  // Painel de avanço rápido (spec #66 / #63)
  let panel;
  if (o.finalizado) {
    panel = `<div class="panel"><div class="small">STATUS ATUAL</div><div class="cur">✓ Pedido finalizado</div></div>`;
  } else if (store.paymentBlocked(o)) {
    panel = `<div class="panel"><div class="small">STATUS ATUAL</div><div class="cur">${payBadge(o.payment.status)}</div>
      <p class="small">Etapas operacionais bloqueadas para este status de pagamento.</p></div>`;
  } else if (o.payment.status !== 'aprovado') {
    panel = `<div class="panel"><div class="small">STATUS ATUAL</div><div class="cur">${payBadge(o.payment.status)}</div>
      <p style="font-weight:700;color:var(--wait)">⏳ AGUARDANDO CONFIRMAÇÃO DO PAGAMENTO</p>
      <p class="small">O faturamento só é liberado após a confirmação oficial do Mercado Pago.</p></div>`;
  } else if (na) {
    panel = `<div class="panel">
      <div class="small">STATUS ATUAL</div><div class="cur">${esc(store.FLOW_STAGES[store.stageIndex(o)-1])}</div>
      <div class="small" style="margin-top:10px">PRÓXIMA ETAPA</div><div style="font-weight:700;margin-bottom:12px">→ ${esc(na.to)}</div>
      <form method="post" action="/admin/orders/${o.id}/advance">
        ${tokenField(req)}<input type="hidden" name="action" value="${na.key}">
        <label>Responsável</label><input name="responsavel" value="Administrador" required>
        <br><button class="btn" type="submit" style="margin-top:12px">${esc(na.label)} →</button>
      </form></div>`;
  } else {
    panel = `<div class="panel"><div class="small">STATUS ATUAL</div><div class="cur">Entregue — pronto para finalizar</div></div>`;
  }

  const logs = o.logs.map(l=>`<tr>
    <td>${esc(l.data)} ${esc(l.hora)}</td><td>${esc(l.field)}</td>
    <td>${esc(l.from)} → <b>${esc(l.to)}</b></td>
    <td><span class="badge ${l.origin==='AUTOMÁTICA'?'b-info':'b-wait'}">${esc(l.origin)}</span></td>
    <td>${esc(l.user)}</td><td class="small">${esc(l.reason||'—')}</td>
  </tr>`).join('');

  const confBlock = cf ? `<div class="card" style="margin-top:12px">
    <b>Origem da confirmação:</b> ${esc(cf.source)}<br>
    <b>ID da transação:</b> ${esc(cf.transactionId||'—')}<br>
    <b>Status retornado:</b> ${esc(cf.statusReturned||'—')}<br>
    <b>Data / Horário:</b> ${esc(cf.data)} ${esc(cf.hora)}
    ${cf.responsavel?`<br><b>Responsável:</b> ${esc(cf.responsavel)} · <b>Motivo:</b> ${esc(cf.motivo)}`:''}
  </div>` : `<p class="small">Sem confirmação de pagamento registrada ainda.</p>`;

  res.send(page(`${o.ref} — TemperoTop`, `
    <a class="btn ghost sm" href="/admin${q(req)}">← Voltar ao painel</a>
    <h1 style="margin-top:14px">${esc(o.ref)}</h1>
    <p class="sub">${new Date(o.createdAt).toLocaleString('pt-BR')}</p>

    <div class="status-row">${payBadge(o.payment.status)} ${opBadge(o.operation)} ${shipBadge(o.shippingStatus)}
      ${o.tracking==='ativo'?'<span class="badge b-info">📡 Acompanhamento ativo</span>':''}</div>

    <div class="grid" style="grid-template-columns:1fr 1fr;align-items:start">
      <div><h2 class="h2" style="margin-top:0">Progresso do pedido</h2>${renderProgress(o)}</div>
      <div><h2 class="h2" style="margin-top:0">Avanço rápido</h2>${panel}</div>
    </div>

    <h2 class="h2">Pagamento</h2>${confBlock}
    <details><summary>Alteração manual excepcional de pagamento</summary>
      <p class="small">Use apenas em exceções. Fica registrado no log com responsável e motivo.</p>
      <form method="post" action="/admin/orders/${o.id}/payment">
        ${tokenField(req)}
        <label>Novo status</label>
        <select name="status" required>
          ${Object.entries(store.PAYMENT).map(([k,v])=>`<option value="${k}"${k===o.payment.status?' selected':''}>${esc(v)}</option>`).join('')}
        </select>
        <label>Usuário responsável</label><input name="responsavel" required placeholder="Seu nome">
        <label>Motivo (obrigatório)</label><input name="motivo" required placeholder="Ex.: confirmação por comprovante">
        <br><button class="btn" type="submit" style="margin-top:12px;background:#8a6d00">Registrar alteração manual</button>
      </form>
    </details>

    <h2 class="h2">Cliente</h2>
    <div class="card"><div class="kv">
      <b>Nome</b><span>${esc(o.customer.nome)}</span><b>E-mail</b><span>${esc(o.customer.email)}</span>
      <b>Telefone</b><span>${esc(o.customer.telefone)}</span><b>CPF</b><span>${esc(o.customer.cpf)}</span>
    </div></div>

    <h2 class="h2">Endereço de envio</h2>
    <div class="card"><div class="kv">
      <b>CEP</b><span>${esc(s.cep)} ${s.cep_validado?'✓ validado':'(não validado)'}</span>
      <b>Rua</b><span>${esc(s.logradouro)}</span><b>Número</b><span>${esc(s.numero)}</span>
      <b>Complemento</b><span>${esc(s.complemento)||'—'}</span><b>Bairro</b><span>${esc(s.bairro)}</span>
      <b>Cidade</b><span>${esc(s.cidade)}</span><b>UF</b><span>${esc(s.estado)}</span>
    </div></div>

    <h2 class="h2">Itens</h2>
    <div class="card"><div class="kv">
      ${o.items.map(i=>`<b>${esc(i.title)}</b><span>${i.quantity} × ${brl(i.unit_price)}</span>`).join('')}
      <b>Total</b><span><strong>${brl(o.total)}</strong></span>
    </div></div>

    <h2 class="h2">Histórico / Auditoria</h2>
    <table><thead><tr><th>Data/Hora</th><th>Campo</th><th>Mudança</th><th>Origem</th><th>Responsável</th><th>Motivo</th></tr></thead>
    <tbody>${logs}</tbody></table>`));
});

/* ---- POST: avançar etapa operacional/envio ---- */
app.post('/admin/orders/:id/advance', adminAuth, (req, res) => {
  const r = store.advance(req.params.id, req.body.action, req.body.responsavel);
  const back = `/admin/orders/${req.params.id}${q(req)}`;
  if (r.error) return res.status(400).send(page('Ação bloqueada', `<h1>Não foi possível avançar</h1><p>${esc(r.error)}</p><a class="btn" href="${back}">Voltar</a>`));
  res.redirect(back);
});

/* ---- POST: alteração manual excepcional de pagamento ---- */
app.post('/admin/orders/:id/payment', adminAuth, (req, res) => {
  const r = store.overridePayment(req.params.id, req.body.status, { motivo: req.body.motivo, responsavel: req.body.responsavel });
  const back = `/admin/orders/${req.params.id}${q(req)}`;
  if (r.error) return res.status(400).send(page('Erro', `<h1>Alteração recusada</h1><p>${esc(r.error)}</p><a class="btn" href="${back}">Voltar</a>`));
  res.redirect(back);
});

app.listen(PORT, () => {
  console.log(`✅ TemperoTop rodando em ${BASE_URL}`);
  console.log(`   Painel: ${BASE_URL}/admin${ADMIN_TOKEN ? '?token=SEU_ADMIN_TOKEN' : ''}`);
  if (ACCESS_TOKEN) console.log('   💳 Pagamento: API Mercado Pago (Access Token) + webhook automático.');
  else if (PAYMENT_LINK) console.log('   💳 Pagamento: LINK do Mercado Pago (confirmação manual no painel).');
  else console.log('   ⚠ Pagamento inativo — defina MP_ACCESS_TOKEN ou MP_PAYMENT_LINK no .env.');
});
