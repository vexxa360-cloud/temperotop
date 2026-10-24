const { chromium } = require('playwright-core');
(async () => {
  const [out, ...fr] = process.argv.slice(2);
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-sandbox'] });
  const p = await (await b.newContext({ viewport: { width: 540, height: 960 }, deviceScaleFactor: 2 })).newPage();
  const errs = []; p.on('console', (m) => ['error', 'warning'].includes(m.type()) && errs.push(m.text())); p.on('pageerror', (e) => errs.push(String(e)));
  await p.goto('http://127.0.0.1:8765/demo/index.html?manual=1&capture=1&phone=1&theme=dark'); await p.waitForFunction('window.__ready');
  await p.evaluate(() => { demo.setPill('CARREGAMENTO INICIAL'); window.m = demo.manual(); window.L = demo.boot({ essential: m.p }); });
  const marks = fr.map(Number); let cur = 0; const last = Math.max(...marks);
  for (; cur <= last; cur++) { await p.evaluate((x) => window.__step(x), cur); if (marks.includes(cur)) await p.screenshot({ path: `${out}_${cur}.png` }); if (cur === 90) { await p.evaluate(() => m.resolve()); await new Promise((r) => setTimeout(r, 30)); } }
  console.log('console:', JSON.stringify(errs)); await b.close();
})();
