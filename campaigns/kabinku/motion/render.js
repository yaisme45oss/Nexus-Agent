const {chromium}=require('playwright');
const path=require('path');
(async()=>{
  const [,,start,end,outDir,fps='30']=process.argv;
  const browser=await chromium.launch();
  const page=await browser.newPage({viewport:{width:1080,height:1920},deviceScaleFactor:1});
  page.on('console',m=>{if(m.type()==='error')console.error('PAGE',m.text())});
  page.on('pageerror',e=>console.error('PAGEERR',e.message));
  await page.goto('file://'+path.resolve(__dirname,'index.html'));
  await page.evaluate(()=>window.ready);
  for(let f=+start;f<+end;f++){
    const t=f/(+fps);
    await page.evaluate(t=>window.renderFrame(t),t);
    await page.screenshot({path:path.join(outDir,String(f).padStart(5,'0')+'.jpg'),type:'jpeg',quality:94});
  }
  await browser.close();
})();
