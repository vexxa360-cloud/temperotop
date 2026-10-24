// Testes do Rango Loader em Chromium real (playwright-core). Uso: NODE_PATH=<node_modules> node tests/loader.test.cjs
const { chromium } = require('playwright-core');
const assert = require('assert');
const BASE = process.env.BASE || 'http://127.0.0.1:8765/demo/index.html';
const results = [];
const T = (name, fn) => results.push({ name, fn });
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
let browser;

async function newPage(opts = {}) {
  const ctx = await browser.newContext({ viewport: opts.viewport || { width: 390, height: 844 }, reducedMotion: opts.reduced ? 'reduce' : 'no-preference', colorScheme: opts.scheme || 'light' });
  const page = await ctx.newPage(); page.issues = [];
  page.on('console', (m) => ['error', 'warning'].includes(m.type()) && page.issues.push(m.text())); page.on('pageerror', (e) => page.issues.push(String(e)));
  await page.goto(`${BASE}?manual=1&${opts.q || ''}`); await page.waitForFunction('window.__ready');
  return page;
}
const exists = (p, sel = '.rl-root, .rl-bar, .rl-local') => p.evaluate((s) => !!document.querySelector(s), sel);
const waitGone = (p, sel, ms = 1500) => p.waitForFunction((s) => !document.querySelector(s), sel, { timeout: ms });

T('inicializacao rapida: libera sem espera artificial apos o requisito ficar pronto', async () => {
  const p = await newPage(); await p.evaluate(() => { window.m = demo.manual(); window.L = demo.boot({ essential: m.p }); });
  assert(await exists(p, '.rl-root'), 'loader deveria aparecer no boot');
  await wait(80); const t0 = Date.now(); await p.evaluate(() => m.resolve()); await waitGone(p, '.rl-root', 800);
  const dt = Date.now() - t0; assert(dt < 650, `saida demorou ${dt}ms`); assert.deepStrictEqual(p.issues, []);
});
T('carregamento demorado: permanece enquanto o requisito essencial esta pendente', async () => {
  const p = await newPage(); await p.evaluate(() => { window.m = demo.manual(); window.L = demo.boot({ essential: m.p }); });
  await wait(3200); assert(await exists(p, '.rl-root'), 'sumiu antes de ficar pronto (loading nao pode expirar por tempo)');
  assert.strictEqual(await p.evaluate(() => L.state), 'showing');
  await p.evaluate(() => m.resolve()); await waitGone(p, '.rl-root');
});
T('requisito secundario nao bloqueia: so as promessas essenciais controlam', async () => {
  const p = await newPage(); await p.evaluate(() => { window.sec = demo.manual(); window.m = demo.manual(); window.L = demo.boot({ essential: m.p }); });
  await p.evaluate(() => m.resolve()); await waitGone(p, '.rl-root'); assert.strictEqual(await p.evaluate(() => document.querySelectorAll('.rl-root').length), 0);
});
T('falha de rede: encerra o loading, emite erro e o app mostra sua propria mensagem', async () => {
  const p = await newPage(); await p.evaluate(() => { window.ev = []; window.m = demo.manual(); window.L = demo.boot({ essential: m.p }); L.on('error', () => ev.push('error')); });
  await p.evaluate(() => m.reject(new Error('Falha de rede. Verifique sua conexão e tente novamente.'))); await waitGone(p, '.rl-root');
  assert.deepStrictEqual(await p.evaluate(() => ev), ['error']); assert(/Falha de rede/.test(await p.textContent('#err')));
});
T('sessao expirada / falha de autenticacao: loading termina e erro e tratado pelo app', async () => {
  const p = await newPage(); await p.evaluate(() => { window.m = demo.manual(); window.L = demo.auth(); L.on('error', () => demo.showError('Sessão expirada. Entre novamente.')); });
  assert(await p.evaluate(() => !!document.querySelector('.rl-auth')), 'versao simplificada de autenticacao');
  assert.strictEqual(await p.evaluate(() => getComputedStyle(document.querySelector('.rl-auth .rl-card')).display), 'none', 'auth nao exibe cards');
  await p.evaluate(() => L.fail(new Error('401'))); await waitGone(p, '.rl-root'); assert(/Sessão expirada/.test(await p.textContent('#err')));
});
T('cancelamento / mudanca de rota: cancel() remove o loading e as animacoes', async () => {
  const p = await newPage(); await p.evaluate(() => { window.ev = []; window.m = demo.manual(); window.L = demo.boot({ essential: m.p }); L.on('cancel', () => ev.push('cancel')); });
  await wait(300); await p.evaluate(() => L.cancel('rota')); await waitGone(p, '.rl-root');
  assert.deepStrictEqual(await p.evaluate(() => ev), ['cancel']); await p.evaluate(() => m.resolve()); await wait(100);
  assert.strictEqual(await p.evaluate(() => document.querySelectorAll('.rl-root').length), 0, 'resolver depois de cancelar nao pode reabrir');
  assert.strictEqual(await p.evaluate(() => document.getAnimations().filter((a) => a.effect?.target?.closest?.('.rl-root')).length), 0);
});
T('AbortSignal cancela o carregamento', async () => {
  const p = await newPage(); await p.evaluate(() => { window.ac = new AbortController(); window.m = demo.manual(); window.L = demo.createRangoLoader({ mode: 'initial', theme: 'dark' }); L.whenReady([m.p], { signal: ac.signal }); });
  await wait(200); assert(await exists(p, '.rl-root')); await p.evaluate(() => ac.abort()); await waitGone(p, '.rl-root');
});
T('desmontagem: destroy() remove DOM e animacoes na hora', async () => {
  const p = await newPage(); await p.evaluate(() => { window.m = demo.manual(); window.L = demo.boot({ essential: m.p }); }); await wait(200);
  await p.evaluate(() => L.destroy()); assert(!(await exists(p, '.rl-root'))); assert.strictEqual(await p.evaluate(() => document.getAnimations().length), 0);
});
T('nao bloqueia a interface depois de pronto', async () => {
  const p = await newPage(); await p.evaluate(() => { window.m = demo.manual(); window.L = demo.boot({ essential: m.p }); }); await wait(100);
  await p.evaluate(() => m.resolve()); await waitGone(p, '.rl-root');
  assert.strictEqual(await p.evaluate(() => document.elementFromPoint(195, 400).tagName), 'IMG', 'elemento sob o ponto deve ser o app');
  await p.click('[data-nav="pedidos"]');
});
T('page: barra aparece so se a operacao demorar (sem piscar) e nao bloqueia cliques', async () => {
  const p = await newPage(); await p.evaluate(() => { window.m = demo.manual(); window.f = demo.nav('pedidos', { essential: m.p }); });
  await wait(40); assert(!(await exists(p, '.rl-bar')), 'barra nao deve aparecer antes de appearAfter');
  await wait(250); assert(await exists(p, '.rl-bar'), 'barra deve aparecer em operacao demorada');
  assert.strictEqual(await p.evaluate(() => getComputedStyle(document.querySelector('.rl-bar')).pointerEvents), 'none');
  await p.evaluate(() => m.resolve()); await waitGone(p, '.rl-bar'); assert(/pedidos/.test(await p.evaluate(() => document.querySelector('#screen').src)));
});
T('page: operacao rapida nunca mostra a barra', async () => {
  const p = await newPage(); await p.evaluate(() => { window.m = demo.manual(); demo.nav('relatorios', { essential: m.p }); }); await wait(30);
  await p.evaluate(() => m.resolve()); await wait(300); assert(!(await exists(p, '.rl-bar')));
});
T('page: varias requisicoes - permanece ate a ultima terminar', async () => {
  const p = await newPage(); await p.evaluate(() => { window.a = demo.manual(); window.b = demo.manual(); window.L = demo.createRangoLoader({ mode: 'page', appearAfter: 0 }); L.track(a.p); L.track(b.p); });
  await p.evaluate(() => a.resolve()); await wait(300); assert(await exists(p, '.rl-bar')); await p.evaluate(() => b.reject(new Error('x'))); await waitGone(p, '.rl-bar');
});
T('local: aria-busy acompanha a operacao e e removido em erro', async () => {
  const p = await newPage(); await p.evaluate(() => { window.m = demo.manual(); window.L = demo.local({ essential: m.p }); });
  assert.strictEqual(await p.getAttribute('#btnLocal', 'aria-busy'), 'true'); await p.evaluate(() => m.reject(new Error('x'))); await waitGone(p, '.rl-local');
  assert.strictEqual(await p.getAttribute('#btnLocal', 'aria-busy'), null);
});
T('acessibilidade: role=status presente; nao ha anuncio por quadro', async () => {
  const p = await newPage(); await p.evaluate(() => { window.m = demo.manual(); demo.boot({ essential: m.p }); });
  assert.strictEqual(await p.evaluate(() => document.querySelectorAll('.rl-root [role=status]').length), 1);
  assert.strictEqual(await p.evaluate(() => document.querySelector('.rl-root [role=status]').getAttribute('aria-live')), 'polite');
  assert.strictEqual(await p.evaluate(() => document.querySelector('.rl-stage').getAttribute('aria-hidden')), 'true');
});
T('movimento reduzido: sem animacoes CSS no loader, composicao estatica e saida imediata', async () => {
  const p = await newPage({ reduced: true }); await p.evaluate(() => { window.m = demo.manual(); window.L = demo.boot({ essential: m.p }); }); await wait(300);
  assert.strictEqual(await p.evaluate(() => document.getAnimations().filter((a) => a.effect?.target?.closest?.('.rl-root')).length), 0, 'nenhuma animacao deveria rodar');
  assert(await p.evaluate(() => getComputedStyle(document.querySelector('.rl-logo')).opacity === '1'), 'logo visivel (estatica)');
  assert((await p.textContent('.rl-root [role=status]')).includes('Carregando'), 'estado nao depende so de cor/movimento');
  await p.evaluate(() => m.resolve()); await waitGone(p, '.rl-root', 300);
});
T('tema: claro usa logo azul sobre branco; escuro usa logo branca sobre azul-marinho', async () => {
  for (const [theme, bg, logo] of [['light', 'rgb(255, 255, 255)', 'rgb(21, 96, 229)'], ['dark', 'rgb(2, 19, 35)', 'rgb(255, 255, 255)']]) {
    const p = await newPage({ q: `theme=${theme}` }); await p.evaluate(() => { window.m = demo.manual(); demo.setTheme(new URLSearchParams(location.search).get('theme')); demo.boot({ essential: m.p }); });
    const c = await p.evaluate(() => ({ bg: getComputedStyle(document.querySelector('.rl-root')).backgroundColor, logo: getComputedStyle(document.querySelector('.rl-logo')).backgroundColor }));
    assert.strictEqual(c.bg, bg, theme); assert.strictEqual(c.logo, logo, theme);
  }
});
T('responsivo: stage dentro da tela e sem rolagem horizontal (celular pequeno, tablet, notebook, desktop)', async () => {
  for (const vp of [{ width: 320, height: 568 }, { width: 390, height: 844 }, { width: 768, height: 1024 }, { width: 1366, height: 768 }, { width: 1920, height: 1080 }]) {
    const p = await newPage({ viewport: vp }); await p.evaluate(() => { window.m = demo.manual(); demo.boot({ essential: m.p }); }); await wait(2200);
    const r = await p.evaluate(() => { const rects = [...document.querySelectorAll('.rl-card, .rl-logo, .rl-tag')].map((e) => e.getBoundingClientRect()); return { l: Math.min(...rects.map((x) => x.left)), r: Math.max(...rects.map((x) => x.right)), t: Math.min(...rects.map((x) => x.top)), b: Math.max(...rects.map((x) => x.bottom)), sw: document.documentElement.scrollWidth, w: innerWidth }; });
    assert(r.l >= -1 && r.r <= vp.width + 1 && r.t >= -1 && r.b <= vp.height + 1, `${vp.width}x${vp.height} elementos fora da tela ${JSON.stringify(r)}`); assert(r.sw <= r.w, 'rolagem horizontal');
  }
});
T('regressao de entrada: o loader nao altera o resultado nem engole erros das promessas do app', async () => {
  const p = await newPage(); const out = await p.evaluate(async () => {
    const L = demo.createRangoLoader({ mode: 'page', appearAfter: 0 }); const ok = await L.track(Promise.resolve(42)); let err = null; try { await L.track(Promise.reject(new Error('boom'))); } catch (e) { err = e.message; } return { ok, err };
  }); assert.deepStrictEqual(out, { ok: 42, err: 'boom' });
});

T('modo contido (dentro do aparelho): ocupa so a tela, abaixo da barra de status e sem vazar', async () => {
  const p = await newPage({ viewport: { width: 540, height: 960 }, q: 'phone=1&theme=dark' });
  await p.evaluate(() => { window.m = demo.manual(); window.L = demo.boot({ essential: m.p }); }); await wait(2200);
  const r = await p.evaluate(() => { const s = document.querySelector('#phoneScreen').getBoundingClientRect(), o = document.querySelector('.rl-root').getBoundingClientRect(), sb = document.querySelector('.sb'); const st = [...document.querySelectorAll('.rl-card, .rl-logo, .rl-tag')].map((e) => e.getBoundingClientRect());
    return { s: [s.left, s.top, s.right, s.bottom], o: [o.left, o.top, o.right, o.bottom], zRoot: +getComputedStyle(document.querySelector('.rl-root')).zIndex, zSb: +getComputedStyle(sb).zIndex, inside: st.every((x) => x.left >= s.left - 1 && x.right <= s.right + 1 && x.top >= s.top - 1 && x.bottom <= s.bottom + 1) }; });
  assert.deepStrictEqual(r.o.map(Math.round), r.s.map(Math.round), 'overlay deve coincidir com a tela'); assert(r.inside, 'elementos devem ficar dentro da tela'); assert(r.zSb > r.zRoot, 'barra de status acima do loader');
  await p.evaluate(() => m.resolve()); await waitGone(p, '.rl-root'); assert.deepStrictEqual(p.issues, []);
});
T('modo contido: barra de pagina fica dentro da tela, logo abaixo da barra de status', async () => {
  const p = await newPage({ viewport: { width: 540, height: 960 }, q: 'phone=1' });
  await p.evaluate(() => { window.m = demo.manual(); demo.nav('pedidos', { essential: m.p, appearAfter: 0 }); }); await wait(250);
  const r = await p.evaluate(() => { const b = document.querySelector('.rl-bar').getBoundingClientRect(), s = document.querySelector('#phoneScreen').getBoundingClientRect(); return { top: b.top - s.top, left: b.left - s.left, w: b.width, sw: s.width }; });
  assert(r.top > 10 && r.top < 80, `topo ${r.top}`); assert(Math.abs(r.w - r.sw) < 2); await p.evaluate(() => m.resolve()); await waitGone(p, '.rl-bar');
});

(async () => {
  browser = await chromium.launch({ executablePath: process.env.CHROME || '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-sandbox'] });
  let fail = 0;
  for (const t of results) { try { await t.fn(); console.log('  ok  ', t.name); } catch (e) { fail++; console.log('  FAIL', t.name, '\n      ', String(e.message).split('\n')[0]); } }
  await browser.close(); console.log(`\n${results.length - fail}/${results.length} testes passaram`); process.exit(fail ? 1 : 0);
})();
