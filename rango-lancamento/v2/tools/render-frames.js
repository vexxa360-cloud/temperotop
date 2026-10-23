const {chromium}=require('playwright-core');
const [k,N]=process.argv.slice(2).map(Number); const FPS=30,TOTAL=900;
(async()=>{
 const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1243/chrome-linux64/chrome',args:['--no-sandbox','--allow-file-access-from-files','--disable-gpu-vsync']});
 const p=await b.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});
 p.on('pageerror',e=>console.log('ERR',e.message));
 await p.goto('file:///home/user/temperotop/rango-lancamento/v2/index.html?render=1'); await p.waitForFunction(()=>window.__ready); await p.waitForTimeout(500);
 const t0=Date.now();
 for(let i=k;i<TOTAL;i+=N){
  await p.evaluate(t=>window.__seek(t),i/FPS);
  await p.screenshot({path:`/tmp/pw/frames/f${String(i).padStart(4,'0')}.jpg`,type:'jpeg',quality:94});
  if(i%30===k) console.log(`w${k} frame ${i} ${((Date.now()-t0)/1000).toFixed(0)}s`);
 }
 await b.close();
})();
