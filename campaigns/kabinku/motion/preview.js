const {chromium}=require('playwright');const path=require('path');
(async()=>{
  const outDir=process.argv[2]; const times=process.argv.slice(3).map(Number);
  const browser=await chromium.launch();
  const page=await browser.newPage({viewport:{width:1080,height:1920},deviceScaleFactor:1});
  page.on('pageerror',e=>console.error('PAGEERR',e.message));
  page.on('console',m=>{if(m.type()==='error')console.error('PAGE',m.text())});
  await page.goto('file://'+path.resolve(__dirname,'index.html'));
  await page.evaluate(()=>window.ready);
  for(const t of times){await page.evaluate(t=>window.renderFrame(t),t);await page.screenshot({path:path.join(outDir,'t'+t.toFixed(2)+'.jpg'),type:'jpeg',quality:85});}
  await browser.close();
})();
