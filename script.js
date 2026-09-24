/* ================= CONFIG ================= */
const PRODUCT_TITLE = 'Porta-Temperos Giratório 360°';
// Opções de quantidade de frascos escolhidas no momento da compra
const VARIANTS = [
  { id: '6',  frascos: 6,  price: 59.90, best: false },
  { id: '8',  frascos: 8,  price: 69.90, best: false },
  { id: '12', frascos: 12, price: 99.90, best: true  }
];
let selectedVariantId = '6';
const getVariant = () => VARIANTS.find(v => v.id === selectedVariantId) || VARIANTS[0];
const variantDesc = v => `${v.frascos} frascos de vidro · Frete grátis com cupom`;
function variantData(v){
  return { id: 'porta-temperos-360-' + v.id, variantId: v.id, title: PRODUCT_TITLE,
    desc: variantDesc(v), frascos: v.frascos, price: v.price };
}

// Endpoints do backend (ver /backend)
const API = {
  config: '/api/config',
  createOrder: '/api/create-order',
  processPayment: '/api/process-payment'
};

const BRL = v => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

/* ================= STATE ================= */
let cart = [];

/* ================= HELPERS ================= */
const $  = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);

/* ================= MOBILE MENU ================= */
const hamburger = $('#hamburger');
const nav = $('#mainNav');
hamburger.addEventListener('click', () => {
  nav.classList.toggle('open');
  hamburger.classList.toggle('active');
});
$$('#mainNav a').forEach(a => a.addEventListener('click', () => {
  nav.classList.remove('open');
  hamburger.classList.remove('active');
}));

/* ================= FAQ ACCORDION ================= */
$$('.faq-item').forEach(item => {
  const q = item.querySelector('.faq-q');
  const a = item.querySelector('.faq-a');
  q.addEventListener('click', () => {
    const open = item.classList.contains('open');
    // close others in same column? keep independent
    if (open) {
      item.classList.remove('open');
      a.style.maxHeight = null;
    } else {
      item.classList.add('open');
      a.style.maxHeight = a.scrollHeight + 'px';
    }
  });
});

/* ================= CART ================= */
const overlay = $('#overlay');
const drawer = $('#cartDrawer');
const cartCount = $('#cartCount');

function openCart(){ drawer.classList.add('open'); overlay.classList.add('show'); }
function closeCart(){ drawer.classList.remove('open'); overlay.classList.remove('show'); }

$('#cartBtn').addEventListener('click', openCart);
$('#cartClose').addEventListener('click', closeCart);
overlay.addEventListener('click', () => { closeCart(); closeModal(); });

function addToCart(){
  const v = variantData(getVariant());
  const existing = cart[0];
  if (existing && existing.variantId === v.variantId) existing.qty++;
  else cart = [{ ...v, qty: 1 }];   // produto único: troca a variante selecionada
  renderCart();
}

/* Seleciona a variante (frascos) e sincroniza carrinho + preços em toda a página */
function selectVariant(id){
  if (!VARIANTS.some(v => v.id === id)) return;
  selectedVariantId = id;
  if (cart.length){
    const v = variantData(getVariant());
    cart = [{ ...v, qty: cart[0].qty || 1 }];
  }
  updateVariantUI();
  renderCart();
}
function updateVariantUI(){
  const v = getVariant();
  document.querySelectorAll('.variant-opt').forEach(el => el.classList.toggle('active', el.dataset.variant === selectedVariantId));
  document.querySelectorAll('[data-price]').forEach(el => el.textContent = BRL(v.price));
  document.querySelectorAll('[data-desc]').forEach(el => el.textContent = variantDesc(v));
}

function renderCart(){
  const body = $('#cartBody');
  const totalQty = cart.reduce((s,i)=>s+i.qty,0);
  cartCount.textContent = totalQty;

  if (!cart.length){
    body.innerHTML = '<p class="cart-empty">Seu carrinho está vazio.</p>';
    $('#checkoutBtn').disabled = true;
    $('#cartTotal').textContent = BRL(0);
    return;
  }
  body.innerHTML = cart.map(i => `
    <div class="cart-line" data-id="${i.id}">
      <div class="thumb"><svg viewBox="0 0 400 480"><use href="#spiceRack"/></svg></div>
      <div class="ci-info">
        <b>${i.title}</b>
        <small>${i.desc}</small>
        <div class="qty">
          <button data-act="dec">−</button><span>${i.qty}</span><button data-act="inc">+</button>
          <button class="ci-remove" data-act="rm">remover</button>
        </div>
      </div>
      <b>${BRL(i.price * i.qty)}</b>
    </div>`).join('');

  const total = cart.reduce((s,i)=>s+i.price*i.qty,0);
  $('#cartTotal').textContent = BRL(total);
  $('#checkoutBtn').disabled = false;

  body.querySelectorAll('.cart-line').forEach(line => {
    const id = line.dataset.id;
    line.querySelectorAll('[data-act]').forEach(btn => {
      btn.addEventListener('click', () => {
        const item = cart.find(i=>i.id===id);
        if (btn.dataset.act==='inc') item.qty++;
        if (btn.dataset.act==='dec') item.qty = Math.max(1, item.qty-1);
        if (btn.dataset.act==='rm') cart = cart.filter(i=>i.id!==id);
        renderCart();
      });
    });
  });
}

/* Variant selectors (frascos) — pílulas na Oferta e no checkout */
$$('.variant-opt').forEach(el => el.addEventListener('click', () => selectVariant(el.dataset.variant)));

/* All "buy" buttons: add + open cart */
$$('[data-buy]').forEach(b => b.addEventListener('click', () => {
  const pick = b.getAttribute('data-variant');
  if (pick) selectVariant(pick);
  addToCart();
  openCart();
}));

/* ================= CHECKOUT MODAL ================= */
const modal = $('#checkoutModal');
function openModal(){
  if(!cart.length) addToCart();
  resetCheckoutSteps();
  modal.classList.add('open'); overlay.classList.add('show'); closeCart();
}
function closeModal(){ modal.classList.remove('open'); }
/* volta sempre para a etapa 1 (dados) ao abrir o checkout */
function resetCheckoutSteps(){
  const step = document.getElementById('paymentStep');
  const f = document.getElementById('checkoutForm');
  if (step) step.hidden = true;
  if (f) f.hidden = false;
  const vp = document.querySelector('.variant-picker-modal'); if (vp) vp.hidden = false;
  const brickBox = document.getElementById('brickContainer');
  if (brickBox) brickBox.innerHTML = '';
  if (brickController) { try { brickController.unmount(); } catch {} brickController = null; }
}

$('#checkoutBtn').addEventListener('click', openModal);
$('#checkoutClose').addEventListener('click', () => { closeModal(); overlay.classList.remove('show'); });

/* ---- simple input masks ---- */
const form = $('#checkoutForm');
const mask = (name, fn) => {
  const el = form.elements[name];
  if (el) el.addEventListener('input', () => { el.value = fn(el.value); });
};
mask('cpf', v => v.replace(/\D/g,'').slice(0,11)
  .replace(/(\d{3})(\d)/,'$1.$2').replace(/(\d{3})(\d)/,'$1.$2').replace(/(\d{3})(\d{1,2})$/,'$1-$2'));
mask('telefone', v => v.replace(/\D/g,'').slice(0,11)
  .replace(/(\d{2})(\d)/,'($1) $2').replace(/(\d{5})(\d{1,4})$/,'$1-$2'));

/* ================= CEP: máscara + busca automática (ViaCEP) ================= */
const cepEl     = form.elements['cep'];
const ruaEl     = form.elements['endereco'];
const bairroEl  = form.elements['bairro'];
const cidadeEl  = form.elements['cidade'];
const estadoEl  = form.elements['estado'];
const numeroEl  = form.elements['numero'];
const cepHint   = document.getElementById('cepHint');
const addrFields = [ruaEl, bairroEl, cidadeEl, estadoEl];

let lastCepQueried = '';

function setHint(msg, type){
  cepHint.textContent = msg || '';
  cepHint.className = 'field-hint' + (type ? ' ' + type : '');
}
/* trava/destrava os campos vindos da API */
function lockAddress(locked){
  addrFields.forEach(el => {
    if (el.tagName === 'SELECT') el.disabled = locked;
    else el.readOnly = locked;
  });
}
function markFilled(filled){
  addrFields.forEach(el => el.classList.toggle('filled', filled));
}
function clearAddress(){
  ruaEl.value = bairroEl.value = cidadeEl.value = '';
  estadoEl.value = '';
  markFilled(false);
}

/* aplica máscara 00000-000 aceitando com ou sem máscara e dispara busca aos 8 dígitos */
cepEl.addEventListener('input', () => {
  const digits = cepEl.value.replace(/\D/g,'').slice(0,8);
  cepEl.value = digits.length > 5 ? digits.replace(/(\d{5})(\d{1,3})/, '$1-$2') : digits;
  if (digits.length === 8) buscarCep(digits);
  else { setHint('', ''); if (digits.length < 8) { lastCepQueried=''; } }
});
/* também busca ao sair do campo (caso cole valor) */
cepEl.addEventListener('blur', () => {
  const digits = cepEl.value.replace(/\D/g,'');
  if (digits.length === 8) buscarCep(digits);
});

async function buscarCep(cep){
  if (cep === lastCepQueried) return;      // evita consulta repetida
  lastCepQueried = cep;

  setHint('Buscando endereço...', 'loading');
  lockAddress(true);
  markFilled(false);

  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 8000);
    const r = await fetch(`https://viacep.com.br/ws/${cep}/json/`, { signal: ctrl.signal });
    clearTimeout(timer);
    if (!r.ok) throw new Error('http');
    const d = await r.json();

    if (d.erro){
      clearAddress();
      lockAddress(false);                  // libera p/ preenchimento manual
      setHint('CEP não encontrado. Verifique o número informado.', 'error');
      ruaEl.focus();
      return;
    }

    ruaEl.value    = d.logradouro || '';
    bairroEl.value = d.bairro || '';
    cidadeEl.value = d.localidade || '';
    estadoEl.value = d.uf || '';

    /* se a API não trouxe rua/bairro (CEP único de cidade), libera esses campos */
    const needsManual = !d.logradouro || !d.bairro;
    lockAddress(!needsManual ? true : false);
    markFilled(true);
    setHint('Endereço encontrado ✓', 'success');
    numeroEl.focus();                      // leva o cursor para "Número"
  } catch (err) {
    clearAddress();
    lockAddress(false);                    // API indisponível: libera manual
    setHint('Não foi possível consultar o CEP agora. Preencha o endereço manualmente.', 'error');
    ruaEl.focus();
  }
}

/* ================= FLUXO DE PAGAMENTO (Bricks, dentro da página) ================= */
const val = n => (form.elements[n]?.value || '').trim();
let currentOrder = null;   // { orderId, ref, amount }
let brickController = null; // instância do Payment Brick

/* Etapa 1 -> valida dados, cria o pedido e abre a etapa de pagamento */
form.addEventListener('submit', async e => {
  e.preventDefault();
  const missing = ['nome','cpf','telefone','email','cep','endereco','numero','bairro','cidade','estado'].filter(n => !val(n));
  if (!form.checkValidity() || missing.length){
    form.reportValidity();
    if (missing.length){
      setHint(!val('endereco') ? 'Informe um CEP válido para preencher o endereço.' : 'Complete os campos do endereço.', 'error');
      form.elements[missing[0]].focus();
    }
    return;
  }

  const btn = $('#payBtn');
  const original = btn.textContent;
  btn.disabled = true; btn.textContent = 'Processando...';
  const restore = () => { btn.disabled = false; btn.textContent = original; };

  const payload = {
    items: cart.map(i => ({ id: i.id, variantId: i.variantId, frascos: i.frascos, title: i.title, description: i.desc, quantity: i.qty, unit_price: i.price })),
    payer: { name: val('nome'), email: val('email'), phone: val('telefone'), identification: { type: 'CPF', number: val('cpf') } },
    shipping: {
      cep: val('cep'), endereco: val('endereco'), numero: val('numero'), complemento: val('complemento'),
      bairro: val('bairro'), cidade: val('cidade'), estado: val('estado')
    }
  };

  let res;
  try {
    res = await fetch(API.createOrder, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
  } catch {
    restore();
    setHint('Servidor de pagamento não está ativo. Rode a pasta "backend" (npm start) e acesse pelo endereço do servidor.', 'error');
    return;
  }
  const ct = res.headers.get('content-type') || '';
  if (!ct.includes('application/json')) {
    restore();
    setHint('Servidor de pagamento não encontrado. Rode o backend e acesse o site por ele (ex.: http://localhost:3000).', 'error');
    return;
  }
  const out = await res.json().catch(() => ({}));
  if (!res.ok) { restore(); setHint(out.error || 'Não foi possível concluir. Verifique os dados.', 'error'); return; }
  if (!out.payment_enabled) {
    restore();
    setHint(`Pedido ${out.ref || ''} registrado. Falta configurar o Mercado Pago (backend/.env) para ativar o pagamento no site.`, 'error');
    return;
  }

  currentOrder = { orderId: out.orderId, ref: out.ref, amount: out.amount };
  restore();
  goToPayment();
});

/* Abre a etapa 2 (pagamento) e renderiza o Payment Brick sem trocar de página */
async function goToPayment(){
  form.hidden = true;
  const vp = $('.variant-picker-modal'); if (vp) vp.hidden = true;  // trava a variante durante o pagamento
  const step = $('#paymentStep');
  step.hidden = false;
  $('#payAmount').textContent = BRL(currentOrder.amount);
  $('#payResult').hidden = true;
  $('#payLoading').style.display = 'block';
  await renderBrick();
}

$('#backToForm').addEventListener('click', async () => {
  if (brickController) { try { await brickController.unmount(); } catch {} brickController = null; }
  $('#brickContainer').innerHTML = '';
  $('#paymentStep').hidden = true;
  const vp = $('.variant-picker-modal'); if (vp) vp.hidden = false;
  form.hidden = false;
});

async function renderBrick(){
  try {
    const cfg = await fetch(API.config).then(r => r.json());
    if (!cfg.publicKey) throw new Error('Public Key ausente');
    const mp = new MercadoPago(cfg.publicKey, { locale: 'pt-BR' });
    const bricks = mp.bricks();

    if (brickController) { try { await brickController.unmount(); } catch {} }
    $('#brickContainer').innerHTML = '';

    brickController = await bricks.create('payment', 'brickContainer', {
      initialization: {
        amount: currentOrder.amount,
        payer: { email: val('email') }
      },
      customization: {
        visual: { style: { theme: 'default' } },
        paymentMethods: {
          creditCard: 'all',
          debitCard: 'all',
          bankTransfer: 'all',   // Pix
          maxInstallments: 12
        }
      },
      callbacks: {
        onReady: () => { $('#payLoading').style.display = 'none'; },
        onError: (err) => {
          console.error('Brick error:', err);
          $('#payLoading').style.display = 'none';
          setPayResult('bad', 'Erro no formulário', 'Não foi possível carregar o pagamento. Recarregue a página e tente novamente.');
        },
        onSubmit: async ({ formData }) => {
          const r = await fetch(API.processPayment, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ orderId: currentOrder.orderId, formData })
          });
          const data = await r.json().catch(() => ({}));
          if (!r.ok) { setPayResult('bad', 'Pagamento não concluído', data.error || 'Tente novamente ou use outro método.'); return; }
          showPaymentOutcome(data);
        }
      }
    });
  } catch (err) {
    console.error(err);
    $('#payLoading').style.display = 'none';
    setPayResult('bad', 'Pagamento indisponível', 'As credenciais do Mercado Pago ainda não foram configuradas no servidor.');
  }
}

function setPayResult(kind, title, msg, extraHTML = ''){
  const el = $('#payResult');
  el.className = 'pay-result ' + kind;
  el.innerHTML = `<h4>${title}</h4><p>${msg}</p>${extraHTML}`;
  el.hidden = false;
}

function showPaymentOutcome(data){
  // status: approved | in_process | pending | rejected
  if (data.status === 'approved'){
    if (brickController) { brickController.unmount().catch(()=>{}); brickController = null; }
    $('#brickContainer').innerHTML = '';
    setPayResult('ok', '✓ Pagamento aprovado!', `Pedido ${currentOrder.ref} confirmado. Obrigado pela compra!`);
    cart = []; renderCart();
  } else if (data.qr_code_base64 || data.qr_code){
    // Pix: mostra QR e código copia-e-cola na própria página
    const img = data.qr_code_base64 ? `<img class="pix-qr" src="data:image/png;base64,${data.qr_code_base64}" alt="QR Code Pix">` : '';
    const code = data.qr_code ? `<div class="pix-code" id="pixCode">${data.qr_code}</div>
      <button type="button" class="btn btn-primary sm copy-btn" id="copyPix">Copiar código Pix</button>` : '';
    setPayResult('pending', 'Quase lá! Pague com Pix', `Escaneie o QR Code ou copie o código. O pedido ${currentOrder.ref} será confirmado após o pagamento.`, img + code);
    const cp = $('#copyPix');
    if (cp) cp.addEventListener('click', () => { navigator.clipboard?.writeText(data.qr_code); cp.textContent = 'Código copiado ✓'; });
  } else if (data.status === 'in_process' || data.status === 'pending'){
    setPayResult('pending', 'Pagamento em análise', `Estamos aguardando a confirmação. Você receberá um aviso assim que o pedido ${currentOrder.ref} for aprovado.`);
  } else {
    setPayResult('bad', 'Pagamento recusado', data.status_detail_msg || 'Não foi aprovado. Tente outro cartão ou método.');
  }
}

/* ================= INIT ================= */
updateVariantUI();
renderCart();
