const {chromium}=require('playwright-core'); const fs=require('fs');
(async()=>{
 const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1243/chrome-linux64/chrome',args:['--no-sandbox','--allow-file-access-from-files']});
 const p=await b.newPage(); p.on('pageerror',e=>console.log('ERR',e.message));
 await p.goto('file:///home/user/temperotop/rango-lancamento/v2/index.html?render=1'); await p.waitForFunction(()=>window.__ready);
 const b64=await p.evaluate(()=>window.__renderAudio()); fs.writeFileSync('/tmp/pw/audio.pcm',Buffer.from(b64,'base64')); console.log('bytes',Buffer.from(b64,'base64').length); await b.close();
})();
