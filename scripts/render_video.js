// Render the page frame by frame to PNGs (serve site/ on :8765 first), then encode with ffmpeg.
const {chromium}=require('playwright');
(async()=>{
  const out=process.argv[2];
  const b=await chromium.launch();
  const p=await b.newPage({viewport:{width:1280,height:720},deviceScaleFactor:1.5});
  await p.goto('http://localhost:8765/index.html');
  await p.waitForFunction(()=>window.__seek);
  await p.addStyleTag({content:'.controls{display:none}'});
  const N=300, step=0.5;
  let i=0;
  for(let m=0;m<=N-1;m+=step){
    await p.evaluate(m=>window.__seek(m),m);
    await p.screenshot({path:`${out}/f${String(i++).padStart(5,'0')}.png`});
  }
  for(let k=0;k<60;k++) await p.screenshot({path:`${out}/f${String(i++).padStart(5,'0')}.png`});
  await b.close();
})();
