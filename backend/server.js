/**
 * Backend TemperoTop — Checkout Transparente (Mercado Pago) + Pós-pagamento (Dropshipping)
 * ---------------------------------------------------------------------------------------
 * Público:
 *   GET  /api/config               → Public Key para o Bricks
 *   POST /api/create-order         → valida + cria o PEDIDO (com endereço via CEP)
 *   POST /api/process-payment      → processa o pagamento no site (Payment API)
 *   POST /api/webhook/mercadopago  → confirma o pagamento sozinho e entra na fila de compra
 *   GET  /api/cep/:cep             → valida CEP (ViaCEP)
 *   GET  /api/order-status         → status do pedido para o CLIENTE (sem dados internos)
 * Admin (protegido por token):
 *   GET  /admin                          → dashboard + fila + lista de pedidos
 *   GET  /admin/orders/:id               → pedido: progresso, compra do fornecedor, log
 *   POST /admin/orders/:id/compra        → registra a compra no fornecedor
 *   POST /admin/orders/:id/envio         → registra rastreio e marca como enviado
 *   POST /admin/orders/:id/advance       → avança etapas simples
 *   POST /admin/orders/:id/payment       → alteração manual excepcional de pagamento
 *   GET  /admin/produtos                 → cadastro do produto (custo, link, margem)
 *   POST /admin/produtos/:sku            → salva dados do produto/fornecedor
 *
 * Dados do fornecedor (custo, link, margem) são ADMIN-ONLY — nunca vão ao cliente.
 */
require('dotenv').config();
const express = require('express');
const path = require('path');
const store = require('./store');
let MercadoPagoConfig, Payment;
try { ({ MercadoPagoConfig, Payment } = require('mercadopago')); } catch { /* npm install */ }

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, '..')));

const ACCESS_TOKEN = process.env.MP_ACCESS_TOKEN;
const PUBLIC_KEY = (process.env.MP_PUBLIC_KEY || '').trim();
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || '';
const PORT = process.env.PORT || 3000;
const BASE_URL = process.env.BASE_URL || `http://localhost:${PORT}`;
const PAYMENT_ENABLED = !!(ACCESS_TOKEN && Payment);

const onlyDigits = s => String(s || '').replace(/\D/g, '');
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]));
const brl = n => 'R$ ' + Number(n || 0).toFixed(2).replace('.', ',');

/* ==================== API pública ==================== */
app.get('/api/config', (req, res) => res.json({ publicKey: PUBLIC_KEY, paymentEnabled: PAYMENT_ENABLED }));

app.get('/api/cep/:cep', async (req, res) => {
  const r = await store.lookupCep(req.params.cep);
  if (r.ok) return res.json(r.data);
  const map = { invalid:{code:400,msg:'CEP inválido. Informe 8 dígitos.'},
    not_found:{code:404,msg:'CEP não encontrado. Verifique o número informado.'},
    unavailable:{code:503,msg:'Não foi possível consultar o CEP agora. Preencha o endereço manualmente.'} };
  const e = map[r.reason] || map.unavailable;
  res.status(e.code).json({ error: e.msg, reason: r.reason });
});

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

app.post('/api/process-payment', async (req, res) => {
  try {
    if (!PAYMENT_ENABLED) return res.status(503).json({ error: 'Pagamento não configurado no servidor (MP_ACCESS_TOKEN).' });
    const { orderId, formData } = req.body;
    const order = store.getOrder(orderId);
    if (!order) return res.status(404).json({ error: 'Pedido não encontrado.' });
    if (!formData || !formData.payment_method_id) return res.status(400).json({ error: 'Dados de pagamento inválidos.' });

    const client = new MercadoPagoConfig({ accessToken: ACCESS_TOKEN });
    const payment = new Payment(client);
    const body = {
      transaction_amount: Number(order.total),           // valor definido no SERVIDOR
      description: 'Porta-Temperos Giratório 360°',
      external_reference: order.id,
      payment_method_id: formData.payment_method_id,
      payer: {
        email: formData.payer?.email || order.customer.email,
        identification: formData.payer?.identification || { type: 'CPF', number: onlyDigits(order.customer.cpf) }
      }
    };
    if (formData.token) body.token = formData.token;
    if (formData.installments) body.installments = Number(formData.installments);
    if (formData.issuer_id) body.issuer_id = formData.issuer_id;

    const result = await payment.create({ body, requestOptions: { idempotencyKey: `${order.id}-${Date.now()}` } });
    store.setPaymentFromProvider(order.id, result.status, { source: 'Mercado Pago / API', transactionId: String(result.id) });

    const tx = result.point_of_interaction?.transaction_data || {};
    res.json({ status: result.status, status_detail: result.status_detail,
      status_detail_msg: statusDetailMsg(result.status_detail), payment_id: result.id,
      qr_code: tx.qr_code || null, qr_code_base64: tx.qr_code_base64 || null });
  } catch (err) {
    console.error('Erro ao processar pagamento:', err?.message || err);
    res.status(400).json({ error: 'Não foi possível processar o pagamento. Verifique os dados e tente novamente.' });
  }
});
function statusDetailMsg(d) {
  const m = { cc_rejected_insufficient_amount:'Saldo/limite insuficiente.',
    cc_rejected_bad_filled_card_number:'Número do cartão inválido.',
    cc_rejected_bad_filled_date:'Data de validade inválida.',
    cc_rejected_bad_filled_security_code:'Código de segurança inválido.',
    cc_rejected_high_risk:'Pagamento recusado por segurança. Tente outro método.',
    cc_rejected_call_for_authorize:'Autorize o pagamento com seu banco e tente de novo.' };
  return m[d] || '';
}

/* Webhook — confirma pagamento e entra na fila de compra automaticamente */
app.post('/api/webhook/mercadopago', async (req, res) => {
  res.sendStatus(200);
  try {
    if ((!ACCESS_TOKEN || !Payment) && req.body?.orderId && req.body?.status) { // modo teste local
      store.setPaymentFromProvider(req.body.orderId, req.body.status, { source: 'Mercado Pago / Webhook (teste)', transactionId: req.body.transactionId || 'TESTE' });
      return;
    }
    const type = req.query.type || req.body?.type;
    const paymentId = req.query['data.id'] || req.body?.data?.id;
    if (type !== 'payment' || !paymentId || !ACCESS_TOKEN || !Payment) return;
    const client = new MercadoPagoConfig({ accessToken: ACCESS_TOKEN });
    const info = await new Payment(client).get({ id: paymentId });
    if (!info.external_reference) return;
    store.setPaymentFromProvider(info.external_reference, info.status, { source: 'Mercado Pago / Webhook', transactionId: String(info.id) });
    console.log(`🔔 Webhook: pedido #${info.external_reference} → "${info.status}"`);
  } catch (err) { console.error('Erro webhook MP:', err); }
});

/* Status do pedido para o CLIENTE — só dados da compra/entrega dele */
app.get('/api/order-status', (req, res) => {
  const ref = onlyDigits(req.query.ref || req.query.id);
  const email = String(req.query.email || '').trim().toLowerCase();
  const o = store.getOrder(ref);
  if (!o || o.customer.email.toLowerCase() !== email)
    return res.status(404).json({ error: 'Pedido não encontrado. Verifique o número e o e-mail.' });
  res.json(store.clientView(o));
});

/* ==================== Painel administrativo ==================== */
function adminAuth(req, res, next) {
  const token = req.query.token || req.body?.token || req.headers['x-admin-token'];
  const isLocal = ['127.0.0.1','::1','::ffff:127.0.0.1'].includes(req.ip);
  if (ADMIN_TOKEN ? token === ADMIN_TOKEN : isLocal) return next();
  res.status(401).send('<h1>401 — Acesso restrito</h1><p>Informe ?token=SEU_ADMIN_TOKEN</p>');
}
const q = req => (req.query.token ? `?token=${encodeURIComponent(req.query.token)}` : '');
const tk = req => (req.query.token ? `<input type="hidden" name="token" value="${esc(req.query.token)}">` : '');

const CSS = `:root{--o:#ea9a2e;--ink:#1c1a17;--line:#e7e2d8;--muted:#6b6459;--ok:#2e7d32;--wait:#b7791f;--bad:#c0392b}
*{box-sizing:border-box}body{font:15px/1.55 system-ui,Segoe UI,Roboto,sans-serif;color:var(--ink);margin:0;background:#f4f1ea}
.wrap{max-width:1080px;margin:0 auto;padding:24px}
h1{margin:0 0 4px}.sub{color:var(--muted);margin:0 0 20px}
a{color:#0a58ca;text-decoration:none}a:hover{text-decoration:underline}
.top{display:flex;gap:16px;align-items:center;margin-bottom:8px;flex-wrap:wrap}
.tabs{display:flex;gap:8px;margin:8px 0 20px}
.tabs a{padding:8px 14px;border-radius:8px;background:#fff;border:1px solid var(--line);color:var(--ink);font-weight:600}
.tabs a.on{background:var(--o);color:#fff;border-color:var(--o)}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:11px 13px;border-bottom:1px solid var(--line);font-size:14px}
th{background:#efe9df;font-weight:700}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:700;white-space:nowrap}
.b-ok{background:#d1e7dd;color:#0f5132}.b-wait{background:#fff3cd;color:#8a6d00}.b-bad{background:#f8d7da;color:#842029}.b-info{background:#cfe2ff;color:#084298}.b-mut{background:#e9ecef;color:#495057}.b-buy{background:#e7dbff;color:#5a2ca0}
.grid{display:grid;gap:14px}.cards{grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.stat b{display:block;font-size:28px;line-height:1.1}.stat span{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.04em}
.h2{margin:24px 0 12px;font-size:17px}
.kv{display:grid;grid-template-columns:170px 1fr;gap:6px 12px}.kv b{color:var(--muted);font-weight:600}
.btn{display:inline-block;background:var(--o);color:#fff;padding:10px 18px;border:none;border-radius:8px;font-weight:700;cursor:pointer;font-size:14px}
.btn:hover{background:#d1841c}.btn.sm{padding:6px 12px;font-size:13px}.btn.ghost{background:#fff;color:var(--ink);border:1px solid var(--line)}.btn.buy{background:#5a2ca0}.btn.buy:hover{background:#48227f}
.queue li{margin:6px 0;list-style:none}.queue .dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:8px}
.prog{list-style:none;margin:0;padding:0}
.prog li{display:flex;align-items:center;gap:12px;padding:5px 0;color:var(--muted)}
.prog .mk{width:24px;height:24px;border-radius:50%;border:2px solid #cfc7b8;display:grid;place-items:center;font-size:13px;flex-shrink:0;background:#fff}
.prog li.done{color:var(--ink)}.prog li.done .mk{background:var(--ok);border-color:var(--ok);color:#fff}
.prog li.cur{color:var(--ink);font-weight:800}.prog li.cur .mk{background:var(--o);border-color:var(--o);color:#fff;box-shadow:0 0 0 4px rgba(234,154,46,.25)}
.status-row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}
.panel{background:#fff8ee;border:1px solid #f0dcb8;border-radius:12px;padding:18px;margin:12px 0}
.panel.buy{background:#f6f1ff;border-color:#e2d4ff}
.panel .cur{font-size:19px;font-weight:800}
.money{display:flex;gap:18px;flex-wrap:wrap;margin:10px 0}
.money div{background:#fff;border:1px solid var(--line);border-radius:10px;padding:10px 14px;min-width:130px}
.money small{color:var(--muted);display:block;font-size:11px;text-transform:uppercase}
.money b{font-size:18px}
details{background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin-top:14px}
summary{cursor:pointer;font-weight:700}
label{display:block;font-size:13px;font-weight:600;color:var(--muted);margin:10px 0 4px}
input,select,textarea{font:inherit;padding:9px 11px;border:1px solid var(--line);border-radius:8px;width:100%;max-width:420px}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:12px;max-width:420px}
.warnbox{background:#fff3cd;border:1px solid #f0dcb8;color:#8a6d00;padding:10px 14px;border-radius:10px;font-weight:600}`;

const page = (title, inner) => `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)}</title><style>${CSS}</style></head>
<body><div class="wrap">${inner}</div></body></html>`;

function payBadge(s){const m={aprovado:['b-ok','Aprovado'],pendente:['b-wait','Pendente'],em_processamento:['b-info','Em processamento'],rejeitado:['b-bad','Rejeitado'],cancelado:['b-bad','Cancelado'],reembolsado:['b-mut','Reembolsado']};const[c,l]=m[s]||['b-mut',s];return `<span class="badge ${c}">💳 ${l}</span>`;}
const fulBadge = f => f ? `<span class="badge b-buy">📦 ${esc(store.FULFILLMENT[f])}</span>` : '';
const shipBadge = s => s==='aguardando' ? '' : `<span class="badge ${s==='entregue'?'b-ok':'b-info'}">🚚 ${esc(store.SHIPPING[s])}</span>`;

function renderProgress(o){
  const cur = store.stageIndex(o);
  return `<ul class="prog">${store.FLOW_STAGES.map((label,i)=>{const n=i+1;const cls=n<cur?'done':n===cur?'cur':'';const mk=n<cur?'✓':n===cur?'●':'○';return `<li class="${cls}"><span class="mk">${mk}</span>${esc(label)}</li>`;}).join('')}</ul>`;
}
const tabs = (req, on) => `<div class="tabs">
  <a href="/admin${q(req)}" class="${on==='pedidos'?'on':''}">Pedidos</a>
  <a href="/admin/produtos${q(req)}" class="${on==='produtos'?'on':''}">Produto / Fornecedor</a></div>`;

/* ---- Dashboard + pedidos ---- */
app.get('/admin', adminAuth, (req, res) => {
  const c = store.dashboard(); const Q = store.actionQueue(); const orders = store.listOrders();
  const stat = (l,v)=>`<div class="card stat"><b>${v}</b><span>${l}</span></div>`;
  const rows = orders.map(o=>`<tr>
    <td><a href="/admin/orders/${o.id}${q(req)}">${esc(o.ref)}</a></td>
    <td>${esc(o.customer.nome)}</td>
    <td>${payBadge(o.payment.status)}</td>
    <td>${o.finalizado?'<span class="badge b-ok">✓ Finalizado</span>':esc(store.FLOW_STAGES[store.stageIndex(o)-1])}</td>
    <td>${brl(o.total)}</td>
  </tr>`).join('') || '<tr><td colspan="5">Nenhum pedido ainda.</td></tr>';
  res.send(page('Meus Pedidos — TemperoTop', `
    <div class="top"><h1>Meus Pedidos</h1></div>${tabs(req,'pedidos')}
    <div class="grid cards">
      ${stat('Pedidos recebidos', c.recebidos)}${stat('Pgto. pendentes', c.pgto_pendente)}
      ${stat('Em processamento', c.pgto_processando)}${stat('Pgto. aprovados', c.pgto_aprovado)}
      ${stat('Aguardando compra', c.aguardando_compra)}${stat('Compra realizada', c.compra_realizada)}
      ${stat('Aguardando envio', c.aguardando_envio)}${stat('Em acompanhamento', c.em_acompanhamento)}
      ${stat('Entregues', c.entregues)}${stat('Finalizados', c.finalizados)}
    </div>
    <h2 class="h2">Próximas ações</h2>
    <div class="card"><ul class="queue" style="padding:0;margin:0">
      <li><span class="dot" style="background:#c0392b"></span><b>${Q.verificar_pgto}</b> pagamento(s) para verificar</li>
      <li><span class="dot" style="background:#5a2ca0"></span><b>${Q.comprar_fornecedor}</b> aguardando <b>compra no fornecedor</b></li>
      <li><span class="dot" style="background:#0a84ff"></span><b>${Q.aguardando_envio}</b> aguardando envio do fornecedor</li>
      <li><span class="dot" style="background:#2e7d32"></span><b>${Q.em_acompanhamento}</b> em acompanhamento</li>
    </ul></div>
    <h2 class="h2">Todos os pedidos</h2>
    <table><thead><tr><th>Pedido</th><th>Cliente</th><th>Pagamento</th><th>Etapa atual</th><th>Total</th></tr></thead><tbody>${rows}</tbody></table>`));
});

/* ---- Detalhe do pedido ---- */
app.get('/admin/orders/:id', adminAuth, (req, res) => {
  const o = store.getOrder(req.params.id);
  if (!o) return res.status(404).send(page('Não encontrado', '<h1>Pedido não encontrado</h1>'));
  const s = o.shipping, cf = o.payment.confirmation, step = store.nextStep(o), C = o.costs;

  // Painel de próxima ação / compra do fornecedor
  let panel = '';
  if (step.type === 'blocked') panel = `<div class="panel"><div class="cur">${payBadge(o.payment.status)}</div><p class="warnbox">Operação bloqueada para este status de pagamento.</p></div>`;
  else if (step.type === 'wait_payment') panel = `<div class="panel"><div class="cur">${payBadge(o.payment.status)}</div><p class="warnbox">⏳ AGUARDANDO CONFIRMAÇÃO DO PAGAMENTO</p><p class="sub">O fluxo do fornecedor só libera após a aprovação oficial do Mercado Pago.</p></div>`;
  else if (step.type === 'form_compra') panel = `
    <div class="panel buy">
      <div class="cur">🛒 Comprar no fornecedor</div>
      <div class="money">
        <div><small>Valor pago pelo cliente</small><b>${brl(C.valorPago)}</b></div>
        <div><small>Custo fornecedor (est.)</small><b>${brl(C.custoFornecedor)}</b></div>
        <div><small>Margem estimada</small><b>${brl(C.margemEstimada)}</b></div>
      </div>
      <div style="display:flex;gap:10px;flex-wrap:wrap;margin:8px 0 14px">
        ${o.supplier.linkProduto?`<a class="btn ghost sm" href="${esc(o.supplier.linkProduto)}" target="_blank" rel="noopener">Abrir produto do fornecedor ↗</a>
        <a class="btn buy sm" href="${esc(o.supplier.linkProduto)}" target="_blank" rel="noopener">Comprar produto ↗</a>`:'<span class="sub">Cadastre o link do fornecedor em “Produto / Fornecedor”.</span>'}
      </div>
      <form method="post" action="/admin/orders/${o.id}/compra">${tk(req)}
        <div class="row2">
          <div><label>Nº do pedido no fornecedor</label><input name="pedidoFornecedor" placeholder="ex.: 123-4567890"></div>
          <div><label>Valor pago ao fornecedor (R$)</label><input name="valorPagoFornecedor" inputmode="decimal" placeholder="ex.: 18,90"></div>
        </div>
        <div class="row2">
          <div><label>Fornecedor</label><input name="fornecedor" value="${esc(o.supplier.fornecedor)}"></div>
          <div><label>Data/hora da compra</label><input name="dataCompra" placeholder="auto se vazio"></div>
        </div>
        <label>Comprovante (link/URL, opcional)</label><input name="comprovante" placeholder="https://...">
        <label>Observações</label><textarea name="observacoes" rows="2" placeholder="opcional"></textarea>
        <label>Responsável</label><input name="responsavel" value="Administrador" required>
        <br><button class="btn buy" type="submit" style="margin-top:12px">Marcar COMPRA REALIZADA →</button>
      </form>
    </div>`;
  else if (step.type === 'form_envio') panel = `
    <div class="panel">
      <div class="cur">🚚 Registrar envio</div>
      <form method="post" action="/admin/orders/${o.id}/envio">${tk(req)}
        <div class="row2">
          <div><label>Código de rastreio</label><input name="codigo" placeholder="ex.: BR123456789BR"></div>
          <div><label>Transportadora</label><input name="transportadora" placeholder="Correios, Jadlog..."></div>
        </div>
        <div class="row2">
          <div><label>Data de postagem</label><input name="dataPostagem" placeholder="auto se vazio"></div>
          <div><label>Link de rastreio (opcional)</label><input name="link" placeholder="https://..."></div>
        </div>
        <label>Responsável</label><input name="responsavel" value="Administrador" required>
        <br><button class="btn" type="submit" style="margin-top:12px">Marcar como ENVIADO →</button>
      </form>
    </div>`;
  else if (step.type === 'action') panel = `
    <div class="panel"><div class="cur">${esc(store.FLOW_STAGES[store.stageIndex(o)-1])}</div>
      <div class="sub" style="margin:8px 0">Próxima etapa: <b>${esc(step.label)}</b></div>
      <form method="post" action="/admin/orders/${o.id}/advance">${tk(req)}<input type="hidden" name="action" value="${step.key}">
        <label>Responsável</label><input name="responsavel" value="Administrador" required>
        <br><button class="btn" type="submit" style="margin-top:12px">${esc(step.label)} →</button></form></div>`;
  else panel = `<div class="panel"><div class="cur">✓ Pedido finalizado</div></div>`;

  const supplierBlock = o.fulfillment && o.fulfillment !== 'aguardando_compra' ? `
    <h2 class="h2">Compra no fornecedor (interno)</h2>
    <div class="card"><div class="kv">
      <b>Fornecedor</b><span>${esc(o.supplier.fornecedor)||'—'}</span>
      <b>Nº pedido fornecedor</b><span>${esc(o.supplier.pedidoFornecedor)||'—'}</span>
      <b>Valor pago fornecedor</b><span>${o.costs.custoReal!=null?brl(o.costs.custoReal):'—'}</span>
      <b>Data da compra</b><span>${esc(o.supplier.dataCompra)||'—'}</span>
      <b>Margem operacional</b><span>${o.costs.margemOperacional!=null?brl(o.costs.margemOperacional):'—'}</span>
      <b>Comprovante</b><span>${o.supplier.comprovante?`<a href="${esc(o.supplier.comprovante)}" target="_blank" rel="noopener">ver ↗</a>`:'—'}</span>
      <b>Observações</b><span>${esc(o.supplier.observacoes)||'—'}</span>
    </div></div>` : '';

  const trackingBlock = o.tracking.codigo ? `
    <h2 class="h2">Rastreio</h2>
    <div class="card"><div class="kv">
      <b>Código</b><span>${esc(o.tracking.codigo)}</span>
      <b>Transportadora</b><span>${esc(o.tracking.transportadora)||'—'}</span>
      <b>Postagem</b><span>${esc(o.tracking.dataPostagem)||'—'}</span>
      <b>Link</b><span>${o.tracking.link?`<a href="${esc(o.tracking.link)}" target="_blank" rel="noopener">rastrear ↗</a>`:'—'}</span>
    </div></div>` : '';

  const logs = o.logs.map(l=>`<tr><td>${esc(l.data)} ${esc(l.hora)}</td><td>${esc(l.field)}</td>
    <td>${esc(l.from)} → <b>${esc(l.to)}</b></td>
    <td><span class="badge ${l.origin==='AUTOMÁTICA'?'b-info':'b-wait'}">${esc(l.origin)}</span></td>
    <td>${esc(l.user)}</td><td class="sub" style="margin:0">${esc(l.reason||'—')}</td></tr>`).join('');

  const confBlock = cf ? `<div class="card"><div class="kv">
      <b>Origem</b><span>${esc(cf.source)}</span><b>ID transação</b><span>${esc(cf.transactionId||'—')}</span>
      <b>Status retornado</b><span>${esc(cf.statusReturned||'—')}</span><b>Data/Hora</b><span>${esc(cf.data)} ${esc(cf.hora)}</span>
      ${cf.responsavel?`<b>Responsável</b><span>${esc(cf.responsavel)}</span><b>Motivo</b><span>${esc(cf.motivo)}</span>`:''}
    </div></div>` : '<p class="sub">Sem confirmação de pagamento ainda.</p>';

  res.send(page(`${o.ref} — TemperoTop`, `
    <a class="btn ghost sm" href="/admin${q(req)}">← Voltar</a>
    <h1 style="margin-top:14px">${esc(o.ref)}</h1><p class="sub">${new Date(o.createdAt).toLocaleString('pt-BR')}</p>
    <div class="status-row">${payBadge(o.payment.status)} ${o.shippingStatus==='aguardando'?fulBadge(o.fulfillment):''} ${shipBadge(o.shippingStatus)}</div>
    <div class="grid" style="grid-template-columns:1fr 1fr;align-items:start">
      <div><h2 class="h2" style="margin-top:0">Progresso</h2>${renderProgress(o)}</div>
      <div><h2 class="h2" style="margin-top:0">Ação atual</h2>${panel}</div>
    </div>
    ${supplierBlock}${trackingBlock}
    <h2 class="h2">Pagamento</h2>${confBlock}
    <details><summary>Alteração manual excepcional de pagamento</summary>
      <p class="sub">Use só em exceções. Fica no log com responsável e motivo.</p>
      <form method="post" action="/admin/orders/${o.id}/payment">${tk(req)}
        <label>Novo status</label><select name="status">${Object.entries(store.PAYMENT).map(([k,v])=>`<option value="${k}"${k===o.payment.status?' selected':''}>${esc(v)}</option>`).join('')}</select>
        <label>Responsável</label><input name="responsavel" required placeholder="Seu nome">
        <label>Motivo (obrigatório)</label><input name="motivo" required placeholder="ex.: confirmação por comprovante">
        <br><button class="btn" type="submit" style="margin-top:12px;background:#8a6d00">Registrar alteração</button></form>
    </details>
    <h2 class="h2">Cliente</h2>
    <div class="card"><div class="kv"><b>Nome</b><span>${esc(o.customer.nome)}</span><b>E-mail</b><span>${esc(o.customer.email)}</span>
      <b>Telefone</b><span>${esc(o.customer.telefone)}</span><b>CPF</b><span>${esc(o.customer.cpf)}</span></div></div>
    <h2 class="h2">Endereço de entrega</h2>
    <div class="card"><div class="kv"><b>CEP</b><span>${esc(s.cep)} ${s.cep_validado?'✓':''}</span><b>Rua</b><span>${esc(s.logradouro)}</span>
      <b>Número</b><span>${esc(s.numero)}</span><b>Complemento</b><span>${esc(s.complemento)||'—'}</span>
      <b>Bairro</b><span>${esc(s.bairro)}</span><b>Cidade</b><span>${esc(s.cidade)}</span><b>UF</b><span>${esc(s.estado)}</span></div></div>
    <h2 class="h2">Itens</h2>
    <div class="card"><div class="kv">${o.items.map(i=>`<b>${esc(i.title)}</b><span>${i.quantity} × ${brl(i.unit_price)} · ${esc(i.variacao||'')}</span>`).join('')}<b>Total</b><span><strong>${brl(o.total)}</strong></span></div></div>
    <h2 class="h2">Histórico / Auditoria</h2>
    <table><thead><tr><th>Data/Hora</th><th>Campo</th><th>Mudança</th><th>Origem</th><th>Responsável</th><th>Obs.</th></tr></thead><tbody>${logs}</tbody></table>`));
});

app.post('/admin/orders/:id/compra', adminAuth, (req, res) => {
  const r = store.registrarCompra(req.params.id, req.body, req.body.responsavel);
  const back = `/admin/orders/${req.params.id}${q(req)}`;
  if (r.error) return res.status(400).send(page('Erro', `<h1>Não foi possível registrar a compra</h1><p>${esc(r.error)}</p><a class="btn" href="${back}">Voltar</a>`));
  res.redirect(back);
});
app.post('/admin/orders/:id/envio', adminAuth, (req, res) => {
  const r = store.registrarEnvio(req.params.id, req.body, req.body.responsavel);
  const back = `/admin/orders/${req.params.id}${q(req)}`;
  if (r.error) return res.status(400).send(page('Erro', `<h1>Não foi possível registrar o envio</h1><p>${esc(r.error)}</p><a class="btn" href="${back}">Voltar</a>`));
  res.redirect(back);
});
app.post('/admin/orders/:id/advance', adminAuth, (req, res) => {
  const r = store.advance(req.params.id, req.body.action, req.body.responsavel);
  const back = `/admin/orders/${req.params.id}${q(req)}`;
  if (r.error) return res.status(400).send(page('Ação bloqueada', `<h1>Não foi possível avançar</h1><p>${esc(r.error)}</p><a class="btn" href="${back}">Voltar</a>`));
  res.redirect(back);
});
app.post('/admin/orders/:id/payment', adminAuth, (req, res) => {
  const r = store.overridePayment(req.params.id, req.body.status, { motivo: req.body.motivo, responsavel: req.body.responsavel });
  const back = `/admin/orders/${req.params.id}${q(req)}`;
  if (r.error) return res.status(400).send(page('Erro', `<h1>Alteração recusada</h1><p>${esc(r.error)}</p><a class="btn" href="${back}">Voltar</a>`));
  res.redirect(back);
});

/* ---- Produto / Fornecedor ---- */
app.get('/admin/produtos', adminAuth, (req, res) => {
  const products = store.listProducts();
  const forms = products.map(p => {
    const variantRows = (p.variants || []).map(v => `
      <tr>
        <td><b>${v.frascos} frascos</b></td>
        <td><input name="preco_${v.id}" value="${v.precoVenda}" style="max-width:120px"></td>
        <td><input name="custo_${v.id}" value="${v.custoFornecedor}" style="max-width:120px"></td>
        <td><b>${brl(store.margemVariante(p, v))}</b></td>
      </tr>`).join('');
    return `
    <div class="card" style="margin-bottom:16px">
      <h3 style="margin:0 0 10px">${esc(p.nome)} <span class="sub" style="font-weight:400">(SKU ${esc(p.sku)})</span></h3>
      <form method="post" action="/admin/produtos/${encodeURIComponent(p.sku)}">${tk(req)}
        <table style="max-width:560px;margin-bottom:12px"><thead><tr><th>Opção</th><th>Preço de venda (R$)</th><th>Custo fornecedor (R$)</th><th>Margem estimada</th></tr></thead>
        <tbody>${variantRows}</tbody></table>
        <div class="row2">
          <div><label>Nome</label><input name="nome" value="${esc(p.nome)}"></div>
          <div><label>Outros custos por pedido (R$)</label><input name="outrosCustos" value="${p.outrosCustos}"></div>
        </div>
        <div class="row2">
          <div><label>Fornecedor</label><input name="fornecedor" value="${esc(p.fornecedor)}"></div>
          <div><label>Status do fornecedor</label><input name="statusFornecedor" value="${esc(p.statusFornecedor)}"></div>
        </div>
        <label>Link do fornecedor (ADMIN — nunca aparece ao cliente)</label>
        <input name="linkFornecedor" value="${esc(p.linkFornecedor)}" placeholder="https://...">
        <br><button class="btn" type="submit" style="margin-top:12px">Salvar produto</button>
      </form>
    </div>`;
  }).join('');
  res.send(page('Produto / Fornecedor — TemperoTop', `
    <div class="top"><h1>Produto / Fornecedor</h1></div>${tabs(req,'produtos')}
    <p class="sub">Preço por opção de frascos (6/8/12). Custo, link e margem são <b>internos</b> — o cliente nunca vê. A margem é calculada por opção (preço − custo − outros custos).</p>
    ${forms}`));
});
app.post('/admin/produtos/:sku', adminAuth, (req, res) => {
  store.updateProduct(req.params.sku, req.body);
  res.redirect(`/admin/produtos${q(req)}`);
});

app.listen(PORT, () => {
  console.log(`✅ TemperoTop rodando em ${BASE_URL}`);
  console.log(`   Painel: ${BASE_URL}/admin${ADMIN_TOKEN ? '?token=SEU_ADMIN_TOKEN' : ''}`);
  console.log(PAYMENT_ENABLED ? '   💳 Pagamento: API Mercado Pago (site) + webhook automático.' : '   ⚠ Pagamento inativo — defina MP_PUBLIC_KEY e MP_ACCESS_TOKEN no .env.');
});
