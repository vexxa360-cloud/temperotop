// Gera o video de exemplo: abertura (voo sobre telas reais, com desfoque de movimento por subquadros) + demonstracao do loader.
// Uso: NODE_PATH=<node_modules> node tools/render-video.cjs <saida.mp4>
const { chromium } = require('playwright-core'); const { spawn, execFileSync } = require('child_process'); const path = require('path'); const os = require('os'); const fs = require('fs');
const OUT = path.resolve(process.argv[2] || 'rango_loader_exemplo.mp4'); const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'rl-'));
const CHROME = process.env.CHROME || '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome'; const BASE = 'http://127.0.0.1:8765/demo/';
const FPS = 30, SUB = 5, SHUTTER = 0.5;
const enc = (args) => { const c = spawn('ffmpeg', ['-y', '-loglevel', 'error', ...args], { stdio: ['pipe', 'inherit', 'inherit'] }); const done = new Promise((r) => c.on('close', r)); return { c, done }; };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function segIntro(b, file) {
  const p = await (await b.newContext({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 })).newPage();
  await p.goto(BASE + 'intro.html'); await p.evaluate(() => window.__ready);
  const e = enc(['-f', 'image2pipe', '-framerate', String(FPS * SUB), '-c:v', 'mjpeg', '-i', '-', '-vf', `tmix=frames=${SUB},select='not(mod(n+1\\,${SUB}))',setpts=N/(${FPS}*TB)`, '-r', String(FPS), '-c:v', 'libx264', '-crf', '17', '-pix_fmt', 'yuv420p', file]);
  const N = 6 * FPS;
  for (let f = 0; f < N; f++) for (let j = 0; j < SUB; j++) {
    const ms = Math.max(0, (f + (j / (SUB - 1) - 0.5) * SHUTTER + 0.25) * 1000 / FPS);
    await p.evaluate((t) => window.__seek(t), ms); e.c.stdin.write(await p.screenshot({ type: 'jpeg', quality: 92 }));
  }
  e.c.stdin.end(); await e.done; await p.close();
}

async function segDemo(b, file) {
  const p = await (await b.newContext({ viewport: { width: 540, height: 960 }, deviceScaleFactor: 2 })).newPage();
  const errs = []; p.on('console', (m) => ['error', 'warning'].includes(m.type()) && errs.push(m.text())); p.on('pageerror', (x) => errs.push(String(x)));
  await p.goto(BASE + 'index.html?manual=1&capture=1&phone=1&theme=dark'); await p.waitForFunction('window.__ready');
  const e = enc(['-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-', '-r', String(FPS), '-c:v', 'libx264', '-crf', '17', '-pix_fmt', 'yuv420p', file]);
  let f = 0; const frame = async () => { await p.evaluate((x) => window.__step(x), f); e.c.stdin.write(await p.screenshot({ type: 'png' })); f++; };
  const hold = async (n) => { for (let i = 0; i < n; i++) await frame(); };
  const act = async (js) => { await p.evaluate(js); await sleep(30); };
  await act(() => { window.__step(0); demo.setPill('CARREGAMENTO INICIAL'); window.m = demo.manual(); window.L = demo.boot({ essential: m.p }); });
  await hold(108); await act(() => m.resolve()); await hold(36);
  await act(() => demo.setPill('CARREGAMENTO DE PÁGINA'));
  for (const s of ['lancar-venda', 'pedidos', 'relatorios', 'dashboard']) {
    await act((s) => { window.m = demo.manual(); demo.nav(s, { essential: m.p, appearAfter: 0 }); }, s).catch(() => {}); 
    await p.evaluate((s) => { window.m = demo.manual(); window.NV = demo.nav(s, { essential: window.m.p, appearAfter: 0 }); }, s); await sleep(30);
    await hold(27); await act(() => m.resolve()); await hold(30);
  }
  await act(() => demo.setPill('CARREGAMENTO LOCAL'));
  await act(() => { window.m = demo.manual(); window.LL = demo.local({ essential: m.p }); }); await hold(30); await act(() => m.resolve()); await hold(24);
  await act(() => { document.getElementById('btnLocal').style.display = 'none'; demo.setPill('AUTENTICAÇÃO'); window.m = demo.manual(); window.AL = demo.auth({ essential: m.p }); });
  await hold(42); await act(() => m.resolve()); await hold(40);
  e.c.stdin.end(); await e.done; await p.close(); return errs;
}

(async () => {
  const b = await chromium.launch({ executablePath: CHROME, args: ['--no-sandbox'] });
  const A = path.join(TMP, 'a.mp4'), B = path.join(TMP, 'b.mp4');
  await segIntro(b, A); console.log('abertura ok'); const errs = await segDemo(b, B); console.log('demo ok; console:', JSON.stringify(errs)); await b.close();
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', A, '-i', B, '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0[v]', '-map', '[v]', '-c:v', 'libx264', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', '30', '-movflags', '+faststart', OUT]);
  console.log('video', OUT);
})();
