// Captura quadros do loader em tempos virtuais (usa __step). Uso: NODE_PATH=... node shot.cjs <tema> <largura> <altura> <saida-prefixo> t1 t2 ...
const { chromium } = require('playwright-core');
(async () => {
  const [theme, w, h, out, ...ts] = process.argv.slice(2);
  const b = await chromium.launch({ executablePath: process.env.CHROME || '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-sandbox'] });
  const p = await (await b.newContext({ viewport: { width: +w, height: +h }, deviceScaleFactor: 1 })).newPage();
  const errs = []; p.on('console', (m) => ['error', 'warning'].includes(m.type()) && errs.push(m.text())); p.on('pageerror', (e) => errs.push(String(e)));
  await p.goto(`http://127.0.0.1:8765/demo/index.html?theme=${theme}&manual=1&capture=1`); await p.waitForFunction('window.__ready');
  await p.evaluate(() => { window.L = demo.boot({ essential: new Promise(() => {}) }); });
  await p.evaluate(() => window.__step(0)); let cur = 0; for (const t of ts) { const f = Math.round(+t * 30); for (; cur <= f; cur++) await p.evaluate((x) => window.__step(x), cur); await p.screenshot({ path: `${out}_${t}.png` }); }
  console.log('console issues:', JSON.stringify(errs)); await b.close();
})();
