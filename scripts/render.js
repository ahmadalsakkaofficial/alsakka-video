// Step 4: render the planned scenes to transparent ProRes 4444 .mov files (30fps) — or quick PNG stills for a preview.
//   node render.js <workdir> [edit] [--stills] [--only name]
//   node render.js <workdir> [edit] --captions   → <workdir>/captions_<edit>.mov (the burned-in captions, from plan_<edit>.json)
// Reads <workdir>/ov_<edit>.json (from build.py plan). Scenes already rendered with the same content are skipped (cache by hash).
const fs=require('fs'),path=require('path'),os=require('os'),{execFileSync}=require('child_process'),{pathToFileURL}=require('url');
const CFG_DIR=path.join(os.homedir(),'.alsakka-video');
const puppeteer=require(path.join(CFG_DIR,'node_modules','puppeteer-core'));
const CAPS=process.argv.includes('--captions'),args=process.argv.slice(2),W=args[0],EDIT=(args[1]&&!args[1].startsWith('--'))?args[1]:'edit',STILLS=args.includes('--stills'),ONLY=args.includes('--only')?args[args.indexOf('--only')+1]:null,FPS=30;
const PLUGIN=path.dirname(__dirname),ASSETS=path.join(PLUGIN,'assets');
const cfgF=path.join(CFG_DIR,'config.json'),C=Object.assign({
  caption_font:path.join(ASSETS,'fonts/Tajawal-Black.ttf'),display_font_black:path.join(ASSETS,'fonts/Tajawal-Black.ttf'),display_font_bold:path.join(ASSETS,'fonts/Tajawal-Bold.ttf'),
  text_font_bold:path.join(ASSETS,'fonts/Tajawal-Bold.ttf'),text_font_regular:path.join(ASSETS,'fonts/Tajawal-Regular.ttf')},Object.fromEntries(Object.entries(fs.existsSync(cfgF)?JSON.parse(fs.readFileSync(cfgF,'utf8')):{}).filter(([k,v])=>v!==null)));
const BROWSERS=['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge','/Applications/Brave Browser.app/Contents/MacOS/Brave Browser','/Applications/Chromium.app/Contents/MacOS/Chromium'];
const ffmpeg=['/opt/homebrew/bin/ffmpeg','/usr/local/bin/ffmpeg',path.join(os.homedir(),'.local/videotools/bin/ffmpeg')].find(p=>fs.existsSync(p))||'ffmpeg';
const ff=(p,w)=>`@font-face{font-family:${w[0]};src:url("${pathToFileURL(p).href}");font-weight:${w[1]}}`;
const FONTS=ff(C.caption_font,['Cap',900])+ff(C.caption_font,['Cap',700])+ff(C.display_font_black,['Disp',900])+ff(C.display_font_bold,['Disp',700])+ff(C.text_font_bold,['Sans',700])+ff(C.text_font_regular,['Sans',500]);
const list=CAPS?[]:JSON.parse(fs.readFileSync(path.join(W,`ov_${EDIT}.json`),'utf8'));
(async()=>{
  const exe=BROWSERS.find(p=>fs.existsSync(p));if(!exe)throw new Error('Google Chrome is needed to draw the scenes — install it from google.com/chrome');
  const br=await puppeteer.launch({executablePath:exe,headless:'new',args:['--no-sandbox','--allow-file-access-from-files','--font-render-hinting=none','--force-color-profile=srgb']});
  const pg=await br.newPage();pg.on('pageerror',e=>console.error('[scene] '+e.message));
  await pg.setViewport({width:1080,height:1920,deviceScaleFactor:1});
  if(CAPS){                 // captions: entrance frames rendered one by one, then a held frame; stitched with exact durations
    const P=JSON.parse(fs.readFileSync(path.join(W,`plan_${EDIT}.json`),'utf8')),dir=path.join(W,'_caps');fs.rmSync(dir,{recursive:true,force:true});fs.mkdirSync(dir,{recursive:true});
    await pg.goto(pathToFileURL(path.join(ASSETS,'scenes','captions.html')).href,{waitUntil:'networkidle0'});await pg.addStyleTag({content:FONTS});await pg.evaluate(()=>document.fonts.ready);
    await pg.evaluate(a=>document.documentElement.style.setProperty('--brand-acc',a),P.accent);
    const blank=path.join(dir,'blank.png');await pg.evaluate(()=>{document.getElementById('cap').style.opacity=0});await pg.screenshot({path:blank,omitBackground:true});
    const L=[];let cur=0,n=0;const push=(f,frames)=>{if(frames>0){L.push(`file '${f}'\nduration ${(frames/FPS).toFixed(6)}`);cur+=frames;}};
    for(const c of P.captions){push(blank,c.a-cur);const len=c.b-c.a,ent=Math.min(8,len);
      await pg.evaluate(c=>window.setup(c),Object.assign({style:P.caption_style},c));
      for(let i=0;i<ent;i++){await pg.evaluate(t=>window.render(t),i/FPS);const f=path.join(dir,`${n++}.png`);await pg.screenshot({path:f,omitBackground:true});push(f,1);}
      if(len>ent){await pg.evaluate(t=>window.render(t),1);const f=path.join(dir,`${n++}.png`);await pg.screenshot({path:f,omitBackground:true});push(f,len-ent);}}
    push(blank,P.dur-cur);L.push(`file '${blank}'`);fs.writeFileSync(path.join(dir,'list.txt'),L.join('\n')+'\n');
    execFileSync(ffmpeg,['-v','error','-y','-f','concat','-safe','0','-i',path.join(dir,'list.txt'),'-vf',`fps=${FPS}`,'-frames:v',String(P.dur),'-c:v','prores_ks','-profile:v','4444','-qscale:v','11','-alpha_bits','8','-pix_fmt','yuva444p10le','-vendor','apl0',path.join(W,`captions_${EDIT}.mov`)]);
    fs.rmSync(dir,{recursive:true,force:true});console.log(`✓ captions ${P.captions.length} → captions_${EDIT}.mov`);await br.close();return;}
  const out=path.join(W,STILLS?'prev':'overlays');fs.mkdirSync(out,{recursive:true});let pack=null;
  for(const o of list){
    if(ONLY&&o.name!==ONLY)continue;
    const mov=path.join(out,o.hash+'.mov');if(!STILLS&&fs.existsSync(mov)){console.log('= '+o.name+' (cached)');continue;}
    if(pack!==o.pack){await pg.goto(pathToFileURL(path.join(ASSETS,'scenes',o.pack+'.html')).href,{waitUntil:'networkidle0'});
      await pg.addStyleTag({content:FONTS});await pg.evaluate(()=>document.fonts.ready);pack=o.pack;}
    await pg.evaluate(o=>{document.documentElement.style.setProperty('--brand-acc',o.brand.acc);document.documentElement.style.setProperty('--brand-bg',o.brand.bg);window.setup(o)},o);
    await pg.evaluate(()=>Promise.all([...document.images].map(i=>i.complete?1:new Promise(r=>{i.onload=i.onerror=r}))));
    if(STILLS){for(const s of (o.stills||[0])){await pg.evaluate(t=>window.render(t),s);await pg.screenshot({path:path.join(out,`${o.name}_${s}.png`),omitBackground:true});}console.log('✓ '+o.name);continue;}
    const N=Math.round(o.dur*FPS),dir=path.join(out,'_f_'+o.hash);fs.rmSync(dir,{recursive:true,force:true});fs.mkdirSync(dir,{recursive:true});
    for(let i=0;i<N;i++){await pg.evaluate(t=>window.render(t),i/FPS);await pg.screenshot({path:path.join(dir,String(i).padStart(4,'0')+'.png'),omitBackground:true});}
    execFileSync(ffmpeg,['-v','error','-y','-framerate',String(FPS),'-i',path.join(dir,'%04d.png'),'-c:v','prores_ks','-profile:v','4444','-qscale:v','11','-alpha_bits','8','-pix_fmt','yuva444p10le','-vendor','apl0',mov]);
    fs.rmSync(dir,{recursive:true,force:true});console.log('✓ '+o.name+' '+N+' frames');
  }
  await br.close();
})().catch(e=>{console.error('⛔',e.message);process.exit(1)});
