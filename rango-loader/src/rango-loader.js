/**
 * Rango Loader — animacao de carregamento (JavaScript puro, sem dependencias).
 *
 * Modos:
 *  - 'initial': abertura completa (cards dos canais convergindo para a logo) enquanto os recursos essenciais carregam.
 *  - 'auth'   : versao simplificada (logo + indicador), para login / recuperacao de sessao.
 *  - 'page'   : barra fina no topo; nao bloqueia a interface.
 *  - 'local'  : indicador inline (3 pontos) dentro de um elemento; marca aria-busy.
 *
 * Regras de design:
 *  - A visibilidade e controlada SOMENTE por estado real: whenReady()/track()/hide()/fail()/cancel().
 *    Nao ha duracao minima, progresso falso nem temporizador para esconder o loading.
 *  - Os unicos temporizadores sao `appearAfter` (evita piscar em cargas muito rapidas) e a limpeza do DOM apos a animacao de saida.
 *  - Nenhuma requisicao e criada aqui; o componente apenas observa promessas fornecidas pelo app.
 *  - Os elementos representam conceitos (canais), nunca dados reais ou simulados.
 */

const CHANNELS = [
  // nomes seguem o menu do Rango; a ordem e a posicao no anel (ax, ay = cos/sen do angulo, rot em graus)
  { id: 'pedidos',    label: 'PEDIDOS',    ax: 0,      ay: -1,     rot: -90, icon: '<path d="M7 3h10l2 3v15l-3-1.5L13 21l-3-1.5L7 21l-3-1.5V6z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="M9 9h6M9 13h6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>' },
  { id: 'entregas',   label: 'ENTREGAS',   ax: 0.951,  ay: -0.309, rot: -18, icon: '<circle cx="6" cy="17" r="3" fill="none" stroke="currentColor" stroke-width="1.8"/><circle cx="18" cy="17" r="3" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M6 17l4-8h5l3 8M9 9H6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>' },
  { id: 'whatsapp',   label: 'WHATSAPP',   ax: 0.588,  ay: 0.809,  rot: 54,  icon: '<path d="M4 5h16v11H9l-5 4z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="M8.5 10.5h.01M12 10.5h.01M15.5 10.5h.01" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/>' },
  { id: 'estoque',    label: 'ESTOQUE',    ax: -0.588, ay: 0.809,  rot: 126, icon: '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="M4 7.5L12 12l8-4.5M12 12v9" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>' },
  { id: 'relatorios', label: 'RELATÓRIOS', ax: -0.951, ay: -0.309, rot: 198, icon: '<path d="M5 20V10M12 20V4M19 20v-7" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/>' },
];

const DEFAULTS = {
  mode: 'initial',          // 'initial' | 'auth' | 'page' | 'local'
  container: null,          // onde montar (padrao: document.body). Outro elemento = modo contido (precisa de position:relative/absolute); em 'local' use `target`
  target: null,             // elemento que recebe o indicador local
  theme: 'auto',            // 'auto' | 'light' | 'dark' | () => 'light' | 'dark'  (integre ao seu provedor de tema)
  appearAfter: undefined,   // ms antes de exibir; padrao: initial/auth = 0, page = 120, local = 200
  reduceMotion: 'auto',     // 'auto' (prefers-reduced-motion) | true | false
  zIndex: undefined,
  labels: { status: 'Carregando o Rango', tagline: 'Sua operação, conectada.' },
};

const mqReduce = () => (typeof matchMedia === 'function' ? matchMedia('(prefers-reduced-motion: reduce)') : null);

function resolveTheme(theme) {
  const t = typeof theme === 'function' ? theme() : theme;
  if (t === 'light' || t === 'dark') return t;
  const el = document.documentElement;
  const attr = el.getAttribute('data-theme');
  if (attr === 'light' || attr === 'dark') return attr;
  if (el.classList.contains('dark')) return 'dark';
  return matchMedia && matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function createRangoLoader(options = {}) {
  const o = { ...DEFAULTS, ...options, labels: { ...DEFAULTS.labels, ...(options.labels || {}) } };
  const mode = o.mode;
  const appearAfter = o.appearAfter ?? ({ initial: 0, auth: 0, page: 120, local: 200 }[mode] ?? 0);
  const events = new EventTarget();
  let root = null, state = 'idle', pending = 0, showTimer = null, cleanupTimer = null, destroyed = false;
  const aborts = new Set();

  const emit = (name, detail) => events.dispatchEvent(new CustomEvent(name, { detail }));
  const reduced = () => o.reduceMotion === true || (o.reduceMotion === 'auto' && !!mqReduce()?.matches);

  function build() {
    const theme = resolveTheme(o.theme);
    const el = document.createElement('div');
    el.setAttribute('data-rl-theme', theme);
    if (reduced()) el.classList.add('rl-reduced');
    if (o.container && o.container !== document.body) el.classList.add('rl-contained'); // ocupa so o container (ex.: tela de um dispositivo)
    if (o.zIndex) el.style.setProperty('--rl-z', String(o.zIndex));
    const sr = `<span class="rl-sr" role="status" aria-live="polite">${o.labels.status}</span>`;
    if (mode === 'initial' || mode === 'auth') {
      el.className += ' rl-root' + (mode === 'auth' ? ' rl-auth' : '');
      const cards = CHANNELS.map((c, i) => `<div class="rl-card" style="--i:${i};--ax:${c.ax};--ay:${c.ay}" aria-hidden="true"><div class="rl-card-in"><div class="rl-card-top"><svg viewBox="0 0 24 24">${c.icon}</svg><b>${c.label}</b></div><div><div class="rl-skel"></div><div class="rl-skel"></div></div></div></div>`).join('');
      const lines = CHANNELS.map((c, i) => `<div class="rl-line" style="--i:${i};--rot:${c.rot}deg" aria-hidden="true"></div><div class="rl-dot" style="--i:${i};--rot:${c.rot}deg" aria-hidden="true"></div>`).join('');
      el.innerHTML = `<div class="rl-persp"><div class="rl-stage" aria-hidden="true"><div class="rl-glow"></div>${lines}${cards}<div class="rl-logo"></div><div class="rl-tag">${o.labels.tagline}</div><div class="rl-wait"><i></i></div></div></div>${sr}`;
    } else if (mode === 'page') {
      el.className += ' rl-bar';
      el.innerHTML = `<i aria-hidden="true"></i>${sr}`;
    } else {
      el.className += ' rl-local';
      el.innerHTML = `<i aria-hidden="true"></i><i aria-hidden="true"></i><i aria-hidden="true"></i>${sr}`;
    }
    return el;
  }

  function mount() {
    if (destroyed || root) return;
    root = build();
    if (mode === 'local') {
      const t = o.target; if (!t) throw new Error('rango-loader: modo "local" exige `target`');
      t.setAttribute('aria-busy', 'true'); t.appendChild(root);
    } else {
      (o.container || document.body).appendChild(root);
    }
    state = 'showing'; emit('show', { mode });
  }

  function show() {
    if (destroyed || state === 'showing' || state === 'exiting') return;
    clearTimeout(showTimer); showTimer = null;
    if (appearAfter > 0) showTimer = setTimeout(() => { showTimer = null; mount(); }, appearAfter); else mount();
  }

  function remove(finalEvent, detail) {
    clearTimeout(showTimer); showTimer = null; clearTimeout(cleanupTimer); cleanupTimer = null;
    const el = root; root = null;
    if (mode === 'local' && o.target) o.target.removeAttribute('aria-busy');
    if (!el) { state = 'idle'; if (finalEvent) emit(finalEvent, detail); return; }
    const done = () => { el.remove(); state = 'idle'; emit('hidden', detail); if (finalEvent) emit(finalEvent, detail); };
    if (reduced() || destroyed) { done(); return; }
    state = 'exiting'; el.classList.add('rl-exit');
    let finished = false; const once = () => { if (!finished) { finished = true; el.removeEventListener('animationend', onEnd); done(); } };
    const onEnd = (e) => { if (e.target === el && /rl-(exit|bar-out)/.test(e.animationName)) once(); };
    el.addEventListener('animationend', onEnd);
    cleanupTimer = setTimeout(once, 600); // so limpeza do DOM caso o navegador nao dispare animationend (ex.: aba em segundo plano)
  }

  const api = {
    get mode() { return mode; },
    get state() { return state; },
    get isVisible() { return state === 'showing' || state === 'exiting'; },
    get element() { return root; },
    /** Exibe o loading (respeitando appearAfter). Em 'initial'/'auth' normalmente e chamado no boot. */
    start() { show(); return api; },
    /** Encerra com sucesso (a interface ja deve estar pronta). */
    hide(detail) { if (state !== 'idle' || showTimer) remove('ready', detail); return api; },
    /** Encerra porque a operacao falhou. O erro continua sendo tratado pelo app (mensagens, retry etc.). */
    fail(error) { if (state !== 'idle' || showTimer) remove('error', { error }); else emit('error', { error }); return api; },
    /** Encerra porque a operacao foi cancelada (troca de rota, abort, desmontagem). */
    cancel(reason) { pending = 0; aborts.forEach((fn) => fn()); aborts.clear(); if (state !== 'idle' || showTimer) remove('cancel', { reason }); return api; },
    /** Remove tudo imediatamente, sem animacao (desmontagem do componente). */
    destroy() { destroyed = true; pending = 0; aborts.clear(); const el = root; root = null; clearTimeout(showTimer); clearTimeout(cleanupTimer); if (el) el.remove(); if (mode === 'local' && o.target) o.target.removeAttribute('aria-busy'); state = 'idle'; },
    /**
     * Acopla o loading aos requisitos ESSENCIAIS da tela (promessas reais fornecidas pelo app).
     * Libera quando todas resolverem; falha rapido se alguma rejeitar; cancela se o signal abortar.
     * Requisicoes secundarias NAO devem ser passadas aqui.
     */
    whenReady(promises, { signal } = {}) {
      show();
      const list = Array.isArray(promises) ? promises : [promises];
      const onAbort = () => api.cancel('abort');
      if (signal) { if (signal.aborted) { api.cancel('abort'); return Promise.resolve(); } signal.addEventListener('abort', onAbort, { once: true }); }
      return Promise.all(list).then(
        (v) => { signal?.removeEventListener('abort', onAbort); if (!signal?.aborted) api.hide(); return v; },
        (e) => { signal?.removeEventListener('abort', onAbort); if (!signal?.aborted) api.fail(e); throw e; },
      );
    },
    /**
     * Contador de operacoes em andamento (para 'page' e 'local'): visivel enquanto houver ao menos uma.
     * Devolve a promessa original (sem alterar resultado nem engolir erros).
     */
    track(promise, { signal } = {}) {
      pending += 1; show();
      let settled = false;
      const dec = () => { if (settled) return; settled = true; aborts.delete(abortFn); pending = Math.max(0, pending - 1); if (pending === 0) (state !== 'idle' || showTimer) ? remove('ready') : null; };
      const abortFn = () => dec();
      if (signal) { if (signal.aborted) dec(); else { aborts.add(abortFn); signal.addEventListener('abort', abortFn, { once: true }); } }
      Promise.resolve(promise).then(dec, dec);
      return promise;
    },
    on(name, fn) { events.addEventListener(name, fn); return () => events.removeEventListener(name, fn); },
  };
  return api;
}

export const CHANNEL_IDS = CHANNELS.map((c) => c.id);
