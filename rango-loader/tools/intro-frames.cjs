const { chromium } = require('playwright-core');
(async () => {
  const [out, ...ts] = process.argv.slice(2);
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome', args: ['--no-sandbox'] });
  const p = await (await b.newContext({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 })).newPage();
  await p.goto('http://127.0.0.1:8765/demo/intro.html'); await p.evaluate(() => window.__ready);
  for (const t of ts) { await p.evaluate((ms) => window.__seek(ms), +t * 1000); await p.screenshot({ path: `${out}_${t}.png` }); }
  await b.close();
})();
