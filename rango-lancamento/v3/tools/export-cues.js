const {chromium}=require('playwright-core'); const fs=require('fs');
(async()=>{ const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1243/chrome-linux64/chrome',args:['--no-sandbox','--allow-file-access-from-files']});
 const p=await b.newPage({viewport:{width:1920,height:1080}}); await p.goto('file:///home/user/temperotop/rango-lancamento/v3/index.html?render=1'); await p.waitForFunction(()=>window.__ready);
 const c=await p.evaluate(()=>window.__cues()); fs.writeFileSync('/tmp/prod/cues.json',JSON.stringify(c)); console.log(c.length,'cues'); await b.close(); })();
